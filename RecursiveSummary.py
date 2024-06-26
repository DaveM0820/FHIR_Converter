import os
from openai import OpenAI
from flask import Flask, Response, json, render_template, jsonify, request
from pathlib import Path
from os import listdir
from os.path import isfile, join
import csv
import pathlib
import asyncio
import threading
import time
from dotenv import load_dotenv
from abc import ABC, abstractmethod

class AIModel(ABC):
    @abstractmethod
    async def generate_stream(self, prompt, model, max_tokens, response_format):
        pass

    @abstractmethod
    async def generate(self, prompt):
        pass

class OpenAIModel(AIModel):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    async def generate_stream(self, prompt, model="gpt-3.5-turbo", max_tokens=16000, response_format = "text"):
        stream = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_format={ "type": response_format},
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate(self, prompt, model="gpt-3.5-turbo", max_tokens=16000, response_format = "text"):
        response = self.client.chat.completions.create(
            model=model,
            response_format={ "type": response_format},
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
'''
class LocalLLMModel(AIModel):
    def __init__(self, model_path):
        self.model = your_local_llm_library.load_model(model_path)

    async def generate_stream(self, prompt):
        # Implement streaming for your local LLM if supported
        # This is a placeholder implementation
        response = self.model.generate(prompt)
        for token in response.split():
            yield token

    async def generate(self, prompt):
        return self.model.generate(prompt)
'''

# Initialize Flask application
app = Flask(__name__)
 
# Initialize OpenAI API client with your API key


# Global variables for data processing
resourceTypes = []  # Store resource types identified in the data
unFormattedData = []  # Store unformatted extracted data
formattedData = []  # Store final formatted data
done = False  # Flag to indicate completion of data processing
streamAllOutput = []  # List to store streaming output from OpenAI API
chunkSize = 5000  # Size of data chunks to be processed
numAttempts = 1  # Number of attempts per chunk for data processing
originalData = ""  # Store the original loaded data
possibleResourceTypes = ""
resourceExamples = ""
currentResourceExamples = ""
USE_OPENAI = True  # Set to False to use local LLM
if USE_OPENAI:
    load_dotenv()
    ai_model = OpenAIModel(os.getenv("OPENAI_API_KEY"))
else:
    ai_model = LocalLLMModel("path/to/your/local/model")
# Concurrency control for shared resources
resource_lock = asyncio.Lock()

"""
The /process_data endpoint receives a POST request with 'chunk_size' and 'num_attempts'. It sets global variables, 
starts asynchronous data processing in a separate thread, and streams the processing output back to the client using 
Server-Sent Events (SSE). The asynchronous process follows these steps: 
1. Splits the original data into smaller chunks based on 'chunk_size'. 
2. For each chunk, identifies potential FHIR resource types using the OpenAI API, running multiple attempts and summarizing results.
3. Extracts relevant data for each chunk based on identified resource types, running multiple attempts and summarizing results.
4. Formats the extracted data into FHIR-compliant JSON, running multiple attempts and summarizing results.
5. Marks processing as complete when all chunks are processed. The overall system functions by loading data, processing it in 
chunks through multiple stages using the OpenAI API, and providing real-time feedback and final formatted data to the user.
"""

# Route to process data asynchronously
@app.route('/process_data', methods=['POST'])
def process_data():
    data = request.get_json()  # Get input data from the request
    global chunkSize, numAttempts, done, streamAllOutput, resourceTypes, unFormattedData, formattedData
    chunkSize = int(data['chunk_size'])  # Set chunk size from input data
    numAttempts = int(data['num_attempts'])  # Set number of attempts from input data
    done = False  # Reset completion flag
    streamAllOutput = []  # Clear previous streaming output
    resourceTypes = []  # Clear previous resource types
    unFormattedData = []  # Clear previous unformatted data
    formattedData = []  # Clear previous formatted data

    # Run the async process_data_async function in a separate thread
    threading.Thread(target=asyncio.run, args=(process_data_async(),)).start()

    # Generator function to stream output to the client
    def generate():
        while not done or streamAllOutput:
            while streamAllOutput:
                token, step, attempt, chunk_num = streamAllOutput.pop(0)
                message = json.dumps({'token': token, 'step': step, 'attempt': attempt, 'chunk_num': chunk_num})
                yield f"data: {message}\n\n"
            time.sleep(0.1)

    return Response(generate(), content_type='text/event-stream')

# Route to load data from text and CSV files
@app.route('/load_data', methods=['GET'])
def load_data():
    global originalData
    originalData = loadTextData() + loadCSVData()  # Load and combine data from files
    word_count = len(originalData.split())  # Calculate word count
    char_count = len(originalData)  # Calculate character count
    return jsonify({'originalData': originalData, 'word_count': word_count, 'char_count': char_count})

def load_resource_types():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'ResourceTypes.txt')
    with open(file_path, 'r') as file:
        return file.read()
    
def load_resource_examples():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'ResourceExamples.txt')
    with open(file_path, 'r') as file:
        content = file.read()
    
    examples = {}
    for resource_example in content.split('|||'):
        resource_example = resource_example.strip()
        if resource_example:
            resource_type = resource_example.split('"resourceType" : "')[1].split('"')[0]
            examples[resource_type] = resource_example
    
    return examples
# Route to render the main page
@app.route('/', methods=['GET'])
def index():
    chunk_size = 2000
    num_attempts = 2
    categories = ""
    unstructured_data = ""
    json_output = ""
    return render_template('index.html', chunk_size=chunk_size, num_attempts=num_attempts, categories=categories, unstructured_data=unstructured_data, json_output=json_output)

# Route to get identified resource types
@app.route('/get_resource_types', methods=['GET'])
def get_resource_types():
    return jsonify(resourceTypes)

# Route to get unformatted extracted data
@app.route('/get_unformatted_data', methods=['GET'])
def get_unformatted_data():
    return jsonify(unFormattedData)

# Route to get formatted final data
@app.route('/get_formatted_data', methods=['GET'])
def get_formatted_data():
    return jsonify(formattedData)

# Route to test the FHIR output with an external server
@app.route('/test_fhir_output', methods=['POST'])
def test_fhir_output():
    data = request.get_json()
    test_results = []

    # Test each chunk of formatted data with the FHIR server
    for chunk_output in data['formatted_data']:
        try:
            response = requests.post('https://hapi.fhir.org/baseR4', json=chunk_output)
            if response.status_code == 200 or response.status_code == 201:
                test_results.append(True)
            else:
                test_results.append(False)
        except Exception as e:
            print(f"Error testing FHIR output: {e}")
            test_results.append(False)
    
    return jsonify(test_results)

# Function to load CSV data from the specified directory
def loadCSVData():
    path = pathlib.Path(__file__).parent.resolve() / "TXTData"
    all_text = ""
    for filename in os.listdir(path):
        if filename.endswith('.csv'):
            file_path = os.path.join(path, filename)
            try:
                with open(file_path, 'r') as file:
                    reader = csv.reader(file)
                    all_text += " ".join([str(row) for row in reader])
            except Exception as e:
                print(f"Failed to read {filename}: {e}")
    return all_text

# Function to load text data from the specified directory
def loadTextData():
    path = pathlib.Path(__file__).parent.resolve() / "TXTData"
    only_files = [f for f in listdir(path) if isfile(join(path, f))]
    all_lines = []
    for file_name in only_files:
        file_path = Path(path) / file_name
        with open(file_path, 'r') as f:
            file_content = f.read()
            all_lines.append(file_content.splitlines())
    words = " ".join([str(item) for item in all_lines])
    return words

# Asynchronous function to process data
async def process_data_async():
    global done
    splitDataResult = splitData(originalData)  # Split the original data into chunks
    tasks = []

    # Create tasks for each chunk to be processed in parallel
    for chunk_index, chunk_data in enumerate(splitDataResult):
        tasks.append(process_chunk(chunk_index, chunk_data))
    
    # Run all chunk processing tasks in parallel
    await asyncio.gather(*tasks)
    
    done = True  # Mark processing as complete

# Asynchronous function to process a single chunk
async def process_chunk(chunk_index, chunk_data):
    try:
        resourceExamples = load_resource_examples()
        allResourceTypes = load_resource_types()
        global currentResourceExamples, resourceTypes
        # Determine resource types for the chunk
        resource_tasks = [determineResourceTypes(chunk_data, attempt, chunk_index + 1) for attempt in range(1, numAttempts + 1)]
        resource_results = await asyncio.gather(*resource_tasks)
        allResourcesForChunk = " ".join(resource_results)
        metaAnalysisOfChunk = await resourceType_meta_summary(chunk_data, allResourcesForChunk, chunk_index + 1)
        chunk_resource_types = [rt.strip() for rt in metaAnalysisOfChunk.split('\n') if rt.strip()]
        # Ensure thread safety when updating shared resourceTypes list
        async with resource_lock:
            resourceTypes.append(chunk_resource_types)
        # Convert categories string to a list of categories
        # Get the resource examples for the identified categories
        for category in chunk_resource_types:
            if category in resourceExamples:
                currentResourceExamples += f"\nExample for {category}:\n{resourceExamples[category]}\n"
    
        print(f"All ResourceExamples: {resourceExamples}")
        print(f"allResourceTypes: {allResourceTypes}")
        print(f"ResourceTypes: {resourceTypes}")

        print(f"currentResourceExamples: {currentResourceExamples}")
        # Extract data for the chunk
        unformatted_data_tasks = [extractData(chunk_data, metaAnalysisOfChunk, attempt, chunk_index + 1) for attempt in range(1, numAttempts + 1)]
        unformatted_data_results = await asyncio.gather(*unformatted_data_tasks)
        allAttemptsForDataChunk = " ".join(unformatted_data_results)
        metaAnalysisOfUnformattedData = await extractedDataFinalResult(chunk_data, allAttemptsForDataChunk, numAttempts + 1, chunk_index + 1)
        
        # Ensure thread safety when updating shared unFormattedData list
        async with resource_lock:
            unFormattedData.append(metaAnalysisOfUnformattedData)
        
        # Format data for the chunk
        formatted_data_tasks = [formatData(metaAnalysisOfUnformattedData, attempt, chunk_index + 1) for attempt in range(1, numAttempts + 1)]
        formatted_data_results = await asyncio.gather(*formatted_data_tasks)
        allAttemptsForFormattedData = " ".join(formatted_data_results)
        finalFormattedData = await formattedDataFinalResult(metaAnalysisOfUnformattedData, allAttemptsForFormattedData, numAttempts + 1, chunk_index + 1)
        
        # Ensure thread safety when updating shared formattedData list
        async with resource_lock:
            formattedData.append(finalFormattedData)
    except Exception as e:
        print(f"Error processing chunk {chunk_index}: {e}")

# Asynchronous function to determine resource types using OpenAI API
async def determineResourceTypes(data, attempt, chunk_num):
    prompt = (
        f"You are an expert medical data analyst who is analyzing the data below. Your goal is to extract information that will eventually be used to convert this data into a FHIR resource. Accuracy and completeness is essential for this task."
        f"Please exclude categories that do not exist in FHIR4. Do not include any additional formatting or text. Only reply with the categories, each on its own line.\n"
        f"The following is a list of valid FHIR4 resources types {possibleResourceTypes}"
        f"\n"
        f"{data}"
    )
    results = []
    try:
        async for chunk in ai_model.generate_stream(prompt):
            results.append(chunk)
            streamAllOutput.append((chunk, 1, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

# Asynchronous function to summarize resource types from multiple attempts
async def resourceType_meta_summary(data, attempt, chunk_num):
    prompt = (
        f"You are an expert medical data analyst who is analyzing the data below. This is a collection of summaries that include a list of FHIR categories "
        f"Please list the valid FHIR4 categories in the following summaries. Please exclude categories that do not exist in FHIR4. Do not include any additional formatting or text. Only reply with the categories, each on its own line.\n"
        f"The following is a list of valid FHIR4 resources types {possibleResourceTypes}"
        f"{data}"
    )
    results = []
    try:
        async for chunk in ai_model.generate_stream(prompt):
            results.append(chunk)
            streamAllOutput.append((chunk, 1, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

# Asynchronous function to extract data based on identified resource types
async def extractData(data, categories, attempt, chunk_num):

    prompt = (
        f"You are an expert medical data analyst who is analyzing the data below. Your goal is to extract information that will eventually be used to convert this data into a FHIR4 resource bundle. Accuracy and completeness is essential for this task. "
        f"Please include ALL data for resources that fall into the following categories: {categories}\n"
        f"Here is example JSON for each FHIR4 resource type: {currentResourceExamples}\n"
        f"Please format your response as follows:\n"
        f"Resource Type: The type of resource that this data applies to.\n"
        f"key:value - This is the key value pair that is used for this resource type. Do not write 'key' or 'value', only the required data. Include as many as required for each resource type. Don't respond with json, just the relevant key:value pairs. Accuracy and completeness are essential. Try to include ALL data.\n"
        f"{data}"
    )
    print(prompt)
    results = []
    try:
        async for chunk in ai_model.generate_stream(prompt):
            results.append(chunk)
            streamAllOutput.append((chunk, 2, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

# Asynchronous function to validate and summarize extracted data
async def extractedDataFinalResult(chunk, summaries, attempt, chunk_num):
    prompt = (
        f"Your job is to act as a critic. You are an expert medical data analyst who is analyzing the data below. This is a collection of summary attempts of the same data. Each summary is attempting to extract valid FHIR4 data. Please analyze the summaries below, look for errors, and reply with the corrected list of data,"
        f"Here is the data being summarized: {chunk}\n"
        f"Here is example JSON for each relevant FHIR4 resource type: {currentResourceExamples}\n"
        f"Here are the attempts at extracting the relevant data: {summaries}\n"
        f"Please format your response as follows:\n"
        f"Resource Type: The type of resource that this data applies to\n"
        f"key:value - This is the key value pair that is used for this resource type. Do not write 'key' or 'value', only the required data. Include as many as required for each resource type. Don't respond with json, just the relevant key:value pairs. Accuracy and completeness are essential. Try to include ALL data.\n"
    )
    results = []
    try:
        async for chunk in ai_model.generate_stream(prompt):
            results.append(chunk)
            streamAllOutput.append((chunk, 2, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

# Asynchronous function to format extracted data into FHIR-compliant JSON
async def formatData(data, attempt, chunk_num):
    prompt = (
        f"Your goal is to convert the data below into a valid FHIR4 resource bundle. Please structure your output in valid JSON that adheres to the FHIR4 standard. Accuracy and completeness is essential. This task will fail if the server rejects the request."
        f"Here is example JSON for each FHIR4 resource type: {currentResourceExamples}\n"
        f"{data}"
    )
    results = []
    try:
        async for chunk in ai_model.generate_stream(prompt, response_format="json_object"):
            results.append(chunk)
            streamAllOutput.append((chunk, 3, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

# Asynchronous function to validate and finalize formatted data
async def formattedDataFinalResult(unformattedData, formattedResults, attempt, chunk_num):
    prompt = (
        f"Below is unformatted data that will be converted to FHIR4 standard, and attempts to convert the data to valid JSON. Look for formatting and syntatical errors, correct them, and output the valid FHIR4 JSON that best matches the provided unformatted data. Accuracy and completeness is essential. This task will fail if the server rejects the request. Please output valid JSON only."
        f"Here is example JSON for each FHIR4 resource type: {currentResourceExamples}\n"

        f"{unformattedData}"
        f"{formattedResults}"
    )
    results = []
    try:
        async for chunk in ai_model.generate_stream(prompt, response_format="json_object"):
            results.append(chunk)
            streamAllOutput.append((chunk, 3, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

# Function to split the original data into smaller chunks
def splitData(words):
    words_array = words.split(" ")
    groups = []
    temp_group = []
    for word in words_array:
        temp_group.append(word)
        if len(temp_group) == chunkSize:
            groups.append(temp_group)
            temp_group = []
    if temp_group:
        groups.append(temp_group)
    newArray = []
    for i, group in enumerate(groups):
        newArray.append(" ".join([str(item) for item in groups[i]]))
    return newArray

if __name__ == '__main__':
    app.run(debug=True)
