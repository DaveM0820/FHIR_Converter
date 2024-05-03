import openai
from openai import OpenAI 
import os
from pathlib import Path
from os import listdir
from os.path import isfile, join
import csv
import pathlib


client = OpenAI(
    api_key=""
)

chunkSize = 2000; #How many words per chunk

def loadCSVData():
    path = pathlib.Path(__file__).parent.resolve() / "TXTData"

    all_text = ""
    for filename in os.listdir(path):
        if filename.endswith('.csv'):
            all_text += "\n" + filename + "\n"
            file_path = os.path.join(path, filename)
            try:
                # Convert all data to string and concatenate
                all_text += " ".join(data.astype(str).values.flatten())
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
    # print (all_lines)
    words = " ".join([str(item) for item in all_lines])
    return words




def determineResourceTypes(data):

        prompt = (f"You are an expert medical data analyst who is analyzing the data below. Your goal is to extract information that will eventually be used to convert this data into a FHIR resource. Accuracy and completeness is essential for this task."
                  f"Please format your response as follows:\n"
                  f"Resource types: Include a list of FHIR4 resource types that apply to the data below.\n"
                  f"\n"
                  f"{data}")
        response = client.chat.completions.create(model="gpt-3.5-turbo",messages=[{"role": "system", "content": prompt},])
        return response.choices[0].message.content

def resourceType_meta_summary(data):
        prompt = (f"You are an expert medical  data analyst who is analyzing the data below. This is a collection of summaries that include a list of FHIR categories "
                  f"Please list the valid FHIR4 categorie in the following summaries. Please exclude categories that do not exist in FHIR4.:\n"
                  f"Summary: put your summary of the included data here\n"
                  f"{data}")
        response = client.chat.completions.create(model="gpt-3.5-turbo",messages=[{"role": "system", "content": prompt},])
        return response.choices[0].message.content

def extractData(data, categories):
        prompt = (f"You are an expert medical data analyst who is analyzing the data below. Your goal is to extract information that will eventually be used to convert this data into a FHIR resource. Accuracy and completeness is essential for this task."
                  f"Please only include data for resource that fall into the following categories: " + categories + "\n"
                  f"Please format your response as follows:\n"
                  f"Resource Type: The type of resource that this data applies to, following this list all the key:value pairs that are required for this resource type. Accuracy and completeness are essential.\n"
                  f"Data(key:value) This is the key value pair that is used for this resource type. Include as many as required for each resource type. Accuracy and completeness are essential."
                  f"{data}")
        response = client.chat.completions.create(model="gpt-3.5-turbo",messages=[{"role": "system", "content": prompt},])
        return response.choices[0].message.content

def extractedDataFinalResult(chunk, summaries):
        prompt = (f"You are an expert medical  data analyst who is analyzing the data below. This is a collection of summaries of the same data. Each summary is attempting to extract valid FHIR4 resources from the data. Please analyize the results below, look for errors, and reply with the correct list of resources,"
                  f"Here is the data being summarized: {chunk}\n"
                  f"Here are the attempts at extracting the relevant data: {summaries}\n"
                  f"Please format your response as follows:\n"
                  f"Resource Type: The type of resource that this data applies to, following this list all the key:value pairs that are required for this resource type. Accuracy and completeness are essential.\n"
                  f"Key: value - This is the key value pair that is used for this resource type. Include as many as required for each resource type. Accuracy and completeness are essential."
                  f"")
        response = client.chat.completions.create(model="gpt-4-turbo",messages=[{"role": "system", "content": prompt},])
        return response.choices[0].message.content
    
def formatData(data):

        prompt = (f"Your goal is to convert the data below into valid FHIR4 resource bundle. Please structure your output in valid JSON that adheres to the FHIR4 standard. Accuracy and competeness is essential. This task will fail if the server rejects the request."
                  f"{data}")
        response = client.chat.completions.create(model="gpt-3.5-turbo",messages=[{"role": "system", "content": prompt},])
        return response.choices[0].message.content

def formattedDataFinalResult(unformattedData, formattedResults):
        prompt = (f"Below is unformatted data that will be converted to FHIR4 standard, and three attempts to convert the data. Look for errors and output the valid the FHIR4 JSON that best matches the provided unformatted data. Accuracy and completeness is essential. This task will fail if the server rejects the request."
                  f"{unformattedData}"
                  f"{formattedResults}"
                  )
        response = client.chat.completions.create(model="gpt-4-turbo",messages=[{"role": "system", "content": prompt},])
        return response.choices[0].message.content    
    
def splitData(words):
    words_array = words.split(" ") 
    groups= []
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

    #print(groups)
    return newArray

def main():
    localData = loadTextData()
    localData += loadCSVData()
    splitDataResult = splitData(localData);
    chunk = 0
    resourceTypes = []
    validResourceTypes = "" #A list of valid FHIR resource types
    validResourceExamples = "" # dictionary matching resource type to exmaple valid data
    #Get Resource Types from the spit data, and then get the meta summary of the resource types
    #Get list of all possible resource types and include in prompt
    for i in splitDataResult:
        print("\nResources for Chunk 1: " + (str)(chunk + 1) + "\n")
        resources = determineResourceTypes(splitDataResult[chunk])
        resourceTypes.append(resources)
        print(resources)
        chunk+=1
    allResourceTypes = " ".join([str(item) for item in resourceTypes])
    print("\nMetaSummary Resources: " + (str)(chunk + 1) + "\n")

    finalResourceTypes = resourceType_meta_summary(allResourceTypes)
    print(finalResourceTypes)
    
    #Get unformatted data for each chunk three times, compare the results and determine the most correct result
    numAttempts = 2; 
    chunk = 0
    unFormattedData = []
    for i in splitDataResult:
        unFormattedDataattempts = []
        for j in range(numAttempts): 
            print("\nUnformatted data for chunk " + (str)(chunk + 1) + ", Attempt: " + (str)(j + 1) + "\n")
            attempt=extractData(splitDataResult[chunk],finalResourceTypes)
            print(attempt)
            unFormattedDataattempts.append(attempt)
        allAttemptsForDataChunk = " ".join([str(item) for item in unFormattedDataattempts])
        metaAnalysisOfChunk = extractedDataFinalResult(splitDataResult[chunk],allAttemptsForDataChunk)
        unFormattedData.append(metaAnalysisOfChunk)
        print("\nUnformatted data data for Chunk " + (str)(chunk + 1) + ", Final Result: ")
        print(metaAnalysisOfChunk)
        chunk+=1

    #Format Data
    numAttempts = 2; 
    chunk = 0
    formattedData = []
    for i in unFormattedData:
        formattedDataAttempts = []
        for j in range(numAttempts): 
            print("\nFormatted data for Chunk " + (str)(chunk + 1) + ", Attempt: " + (str)(j + 1) + "\n")
            attempt=formatData(unFormattedData[chunk])
            print(attempt)
            formattedDataAttempts.append(attempt)
        allAttemptsForDataChunk = " ".join([str(item) for item in formattedDataAttempts])
        finalFormattedData = formattedDataFinalResult(unFormattedData[chunk], formattedDataAttempts[chunk])
        formattedData.append(finalFormattedData)
        print("\nFinal JSON for chunk " + (str)(chunk + 1) + ", Final Result: ")
        print(metaAnalysisOfChunk)
        chunk+=1


if __name__ == "__main__":
    main()
