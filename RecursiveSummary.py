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
import json

# Initialize Flask
app = Flask(__name__)
# Initialize OpenAI API key
client = OpenAI()
client.api_key = os.getenv('OPENAI_API_KEY')

# Global variables
resourceTypes = []
unFormattedData = []
formattedData = []
done = False
streamAllOutput = []
chunkSize = 2000
numAttempts = 2
originalData = ""

@app.route('/process_data', methods=['POST'])
def process_data():
    data = request.get_json()
    global chunkSize, numAttempts, done, streamAllOutput
    chunkSize = int(data['chunk_size'])
    numAttempts = int(data['num_attempts'])
    done = False
    streamAllOutput = []

    # Run the async process_data_async in a separate thread
    threading.Thread(target=asyncio.run, args=(process_data_async(),)).start()

    def generate():
        while not done or streamAllOutput:
            while streamAllOutput:
                token, step, attempt, chunk_num = streamAllOutput.pop(0)
                message = json.dumps({'token': token, 'step': step, 'attempt': attempt, 'chunk_num': chunk_num})
                yield f"data: {message}\n\n"
            time.sleep(0.1)

    return Response(generate(), content_type='text/event-stream')

@app.route('/load_data', methods=['GET'])
def load_data():
    global originalData
    originalData = loadTextData() + loadCSVData()
    word_count = len(originalData.split())
    char_count = len(originalData)
    return jsonify({'originalData': originalData, 'word_count': word_count, 'char_count': char_count})

@app.route('/', methods=['GET'])
def index():
    chunk_size = 2000
    num_attempts = 2
    categories = ""
    unstructured_data = ""
    json_output = ""
    return render_template('index.html', chunk_size=chunk_size, num_attempts=num_attempts, categories=categories, unstructured_data=unstructured_data, json_output=json_output)

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

async def process_data_async():
    global done
    splitDataResult = splitData(originalData)
    chunk = 0
    for i in splitDataResult:
        resourceAttempts = []
        for j in range(numAttempts):
            resources = await determineResourceTypes(splitDataResult[chunk], j + 1, chunk + 1)
            resourceAttempts.append(resources)
        allResourcesForChunk = " ".join([str(item) for item in resourceAttempts])
        metaAnalysisOfChunk = await resourceType_meta_summary(splitDataResult[chunk], allResourcesForChunk)
        resourceTypes.append(metaAnalysisOfChunk)
        chunk += 1
    chunk = 0
    for i in splitDataResult:
        unFormattedDataattempts = []
        for j in range(numAttempts):
            attempt = await extractData(splitDataResult[chunk], resourceTypes[chunk], j + 1, chunk + 1)
            unFormattedDataattempts.append(attempt)
        allAttemptsForDataChunk = " ".join([str(item) for item in unFormattedDataattempts])
        metaAnalysisOfChunk = await extractedDataFinalResult(splitDataResult[chunk], allAttemptsForDataChunk, len(unFormattedDataattempts)+1, chunk + 1)
        unFormattedData.append(metaAnalysisOfChunk)
        chunk += 1
    chunk = 0
    for i in unFormattedData:
        formattedDataAttempts = []
        for j in range(numAttempts):
            attempt = await formatData(unFormattedData[chunk], j + 1, chunk + 1)
            formattedDataAttempts.append(attempt)
        allAttemptsForDataChunk = " ".join([str(item) for item in formattedDataAttempts])
        finalFormattedData = await formattedDataFinalResult(unFormattedData[chunk], formattedDataAttempts[chunk], len(formattedDataAttempts)+1, chunk + 1)
        formattedData.append(finalFormattedData)
        chunk += 1
    done = True

async def determineResourceTypes(data, attempt, chunk_num):
    prompt = (
        f"You are an expert medical data analyst who is analyzing the data below. Your goal is to extract information that will eventually be used to convert this data into a FHIR resource. Accuracy and completeness is essential for this task."
        f"Please format your response as follows:\n"
        f"Resource types: Include a list of FHIR4 resource types that apply to the data below.\n"
        f"\n"
        f"{data}"
    )
    results = []
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    try:
        for chunk in stream:
            if chunk.choices[0].delta.content:
                results.append(chunk.choices[0].delta.content)
                streamAllOutput.append((chunk.choices[0].delta.content, 1, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

async def resourceType_meta_summary(data, attempts):
    prompt = (
        f"You are an expert medical data analyst who is analyzing the data below. This is a collection of summaries that include a list of FHIR categories "
        f"Please list the valid FHIR4 categories in the following summaries. Please exclude categories that do not exist in FHIR4.:\n"
        f"Summary: put your summary of the included data here\n"
        f"{data}"
    )
    results = []
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    try:
        for chunk in stream:
            if chunk.choices[0].delta.content:
                results.append(chunk.choices[0].delta.content)
                streamAllOutput.append((chunk.choices[0].delta.content, 1, attempt, 1))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

async def extractData(data, categories, attempt, chunk_num):
    prompt = (
        f"You are an expert medical data analyst who is analyzing the data below. Your goal is to extract information that will eventually be used to convert this data into a FHIR resource. Accuracy and completeness is essential for this task."
        f"Please only include data for resources that fall into the following categories: {categories}\n"
        f"Please format your response as follows:\n"
        f"Resource Type: The type of resource that this data applies to, following this list all the key:value pairs that are required for this resource type. Accuracy and completeness are essential.\n"
        f"Data(key:value) This is the key value pair that is used for this resource type. Include as many as required for each resource type. Accuracy and completeness are essential."
        f"{data}"
    )
    results = []
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    try:
        for chunk in stream:
            if chunk.choices[0].delta.content:
                results.append(chunk.choices[0].delta.content)
                streamAllOutput.append((chunk.choices[0].delta.content, 2, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

async def extractedDataFinalResult(chunk, summaries, attempt, chunk_num):
    prompt = (
        f"You are an expert medical data analyst who is analyzing the data below. This is a collection of summaries of the same data. Each summary is attempting to extract valid FHIR4 resources from the data. Please analyze the results below, look for errors, and reply with the correct list of resources,"
        f"Here is the data being summarized: {chunk}\n"
        f"Here are the attempts at extracting the relevant data: {summaries}\n"
        f"Please format your response as follows:\n"
        f"Resource Type: The type of resource that this data applies to, following this list all the key:value pairs that are required for this resource type. Accuracy and completeness are essential.\n"
        f"Key: value - This is the key value pair that is used for this resource type. Include as many as required for each resource type. Accuracy and completeness are essential."
    )
    results = []
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    try:
        for chunk in stream:
            if chunk.choices[0].delta.content:
                results.append(chunk.choices[0].delta.content)
                streamAllOutput.append((chunk.choices[0].delta.content, 2, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

async def formatData(data, attempt, chunk_num):
    prompt = (
        f"Your goal is to convert the data below into a valid FHIR4 resource bundle. Please structure your output in valid JSON that adheres to the FHIR4 standard. Accuracy and completeness is essential. This task will fail if the server rejects the request."
        f"{data}"
    )
    results = []
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    try:
        for chunk in stream:
            if chunk.choices[0].delta.content:
                results.append(chunk.choices[0].delta.content)
                streamAllOutput.append((chunk.choices[0].delta.content, 3, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

async def formattedDataFinalResult(unformattedData, formattedResults, attempt, chunk_num):
    prompt = (
        f"Below is unformatted data that will be converted to FHIR4 standard, and three attempts to convert the data to valid JSON. Look for errors and output the valid FHIR4 JSON that best matches the provided unformatted data. Accuracy and completeness is essential. This task will fail if the server rejects the request. Please output valid JSON only."
        f"{unformattedData}"
        f"{formattedResults}"
    )
    results = []
    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    try:
        for chunk in stream:
            if chunk.choices[0].delta.content:
                results.append(chunk.choices[0].delta.content)
                streamAllOutput.append((chunk.choices[0].delta.content, 3, attempt, chunk_num))
    except Exception as e:
        print(f"Error during streaming: {e}")
    return ''.join(results)

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
