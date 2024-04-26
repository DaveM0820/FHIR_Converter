import openai
from pathlib import Path
from os import listdir
from os.path import isfile, join
import csv
import pathlib
from openai import OpenAI

client = OpenAI(
api_key=""
)
#summaries = [,]  [summary level, summary number]

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


def summarize_data(data):

        prompt = (f"You are an expert medical professional data analyst who is analyzing the data below. "
                  f"Please format your response as follows:\n"
                  f"Summary: put your summary of the included data here\n"
                  f"Categories: include a list of categories that apply to the data below\n"
                  f"Anomalies: Note any particular anomalies in the data\n"
                  f"Insights: Please note any patterns or insights that can be gleaned from this data\n\n"
                  f"{data}")
        response = client.chat.completions.create(model="gpt-3.5-turbo",messages=[{"role": "system", "content": prompt},])
        return response.choices[0].message.content

def meta_summary(data):
        prompt = (f"You are an expert medical professional data analyst who is analyzing the data below. This is a collection of summaries you previous generated. Please summarize these summaries"
                  f"Please format your response as follows:\n"
                  f"Summary: put your summary of the included data here\n"
                  f"Categories: include a list of categories that apply to the data below\n"
                  f"Anomalies: Note any particular anomalies in the data\n"
                  f"Insights: Please note any patterns or insights that can be gleaned from this data\n\n"
                  f"{data}")
        response = client.chat.completions.create(model="gpt-3.5-turbo",messages=[{"role": "system", "content": prompt},])
        return response.choices[0].message.content

    
def splitData(words):
    words_array = words.split(" ") 
    groups= []
    temp_group = []
    for word in words_array:
        temp_group.append(word)
        if len(temp_group) == 2000:
            
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
    splitDataResult = splitData(localData);
    chunk = 0
    summaries = []
    for i in splitDataResult:
        print("Summary " + str(chunk))
        print(summarize_data(splitDataResult[chunk]))
        summaries.append(summarize_data(splitDataResult[chunk]))
        chunk+=1

    allsummaries = " ".join([str(item) for item in summaries])

    print("Meta analysis")
    print(meta_summary(allsummaries))
    summarizationLevel = 0
    summaryNumber = 0
    
    CSV_directory_path = '/CSVData'
    csv_data = loadTextData()
    openai.api_key = "YOUR_OPENAI_API_KEY"

if __name__ == "__main__":
    main()
