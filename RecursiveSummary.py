from openai import OpenAI
from pathlib import Path
from os import listdir
from os.path import isfile, join
import csv
import pathlib
from fhirclient import client
from fhirclient.models import patient

openAIClient = OpenAI(
    api_key="API-KEY",
)

#summaries = [,]  [summary level, summary number]
def loadFHIRData():
        settings = {
        'app_id': 'my_web_app',
        'api_base': 'https://hapi.fhir.org/baseR4',
    }
    smart = client.FHIRClient(settings=settings)
    all_patients = patient.Patient.where(struct={'_count': 1000}).perform_resources(smart.server)
    for patient_resource in all_patients:
        print(patient_resource.name[0].given[0], patient_resource.name[0].family)

def loadTextData(root_dir):
    path = pathlib.Path(__file__).parent.resolve() / "TXTData"
    only_files = [f for f in listdir(path) if isfile(join(path, f))]
    all_lines = []
    for file_name in only_files:
        file_path = Path(path) / file_name
        with open(file_path, 'r') as f:
            file_content = f.read()
            all_lines.append(file_content.splitlines())
    # print (all_lines)
    return (all_lines)
    directory = pathlib.Path(__file__).parent.resolve() / "CSVData"
    for root,dirs,files in os.walk(directory):
        for file in files:
           if file.endswith(".csv"):
               f=open(file, 'r')
               all_lines.append(r)
               f.close()
    words = ""
    for i in all_lines: 
      words += i
    print(words)
    words_array = words.split(" ") 
    groups_of_20000 = []
    temp_group = []
    for word in words_array:
        temp_group.append(word)
        if len(temp_group) == 20000:
            groups_of_20000.append(temp_group)
            temp_group = []
    
    if temp_group:
        groups_of_20000.append(temp_group)

    for i, group in enumerate(groups_of_20000):
        print(f"Group {i+1}: {group}")

    print(groups_of_20000)
    return groups_of_20000

def summarize_data(data, initial=False):
    if initial:
        prompt = (f"You are an expert medical professional data analyst who is analyzing the data below. "
                  f"Please format your response as follows:\n"
                  f"Summary: put your summary of the included data here\n"
                  f"Categories: include a list of categories that apply to the data below\n"
                  f"Anomalies: Note any particular anomalies in the data\n"
                  f"Insights: Please note any patterns or insights that can be gleaned from this data\n\n"
                  f"{data}")
    else:
        prompt = (f"You are summarizing the previous summaries. Please consolidate the information below into a comprehensive summary:\n\n"
                  f"{data}")
    response = openAIClient.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system","content": prompt}]
    )
    return response.choices[0].message.content

def recursive_summarize(summaries, level=0):
    if len(summaries) == 1:
        return summaries[0]
    new_summaries = []
    # Assume each summary can fit within the GPT-4 context window
    chunk_size = 2  # Adjust based on actual context window capacity and summary lengths
    for i in range(0, len(summaries), chunk_size):
        chunked_data = ' '.join(summaries[i:i+chunk_size])
        new_summary = summarize_data(chunked_data, initial=False)
        new_summaries.append(new_summary)
    return recursive_summarize(new_summaries, level + 1)

def splitData:
    return ""

def main():
    localdata = loadTextData()
    fhirdata = loadFHIRData()
    summaries = [,]
    summaries[0] = slitData()
    summarizationLevel = 0
    summaryNumber = 0
    for chunk in dataChunks
        summaries[0,summaryNumber] = summarizeData(chunk,true)
        summaryNumber ++
    
    
    CSV_directory_path = '/CSVData'
    csv_data = loadTextData(CSV_directory_path)
    # print(csv_data)  # Prints all CSV row data as a list of strings
    openai.api_key = "YOUR_OPENAI_API_KEY"
    #data_chunks = load_data()
    #initial_summaries = [summarize_data(chunk, initial=True) for chunk in data_chunks]
    #final_summary = recursive_summarize(initial_summaries)
    #print("Final Summary:", final_summary)
if __name__ == "__main__":
    main()





