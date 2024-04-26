import openai
from pathlib import Path
from os import listdir
from os.path import isfile, join
import csv
import pathlib

def loadTextData(root_dir):
    path = pathlib.Path(__file__).parent.resolve() / "TXTData"
    only_files = [f for f in listdir(path) if isfile(join(path, f))]
    all_lines = []
    for file_name in only_files:
        file_path = Path(path) / file_name
        with open(file_path, 'r') as f:
            file_content = f.read()
            all_lines.append(file_content.splitlines())
    print (all_lines)
    return (all_lines)
    directory = pathlib.Path(__file__).parent.resolve() / "CSVData"
    for root,dirs,files in os.walk(directory):
        for file in files:
           if file.endswith(".csv"):
               f=open(file, 'r')
               all_lines.append(r)
               f.close()
    string = "";
    for i in all_lines: 
      string += i
    #print (string)

    return string


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
    response = openai.Completion.create(
        model="gpt-4-turbo",
        prompt=prompt,
        max_tokens=2048
    )
    return response.choices[0].text.strip()

def recursive_summarize(summaries, level=0):
    if len(summaries) == 1:
        return summaries[0]  # Final summary achieved
    new_summaries = []
    # Assume each summary can fit within the GPT-4 context window
    chunk_size = 2  # Adjust based on actual context window capacity and summary lengths
    for i in range(0, len(summaries), chunk_size):
        chunked_data = ' '.join(summaries[i:i+chunk_size])
        new_summary = summarize_data(chunked_data, initial=False)
        new_summaries.append(new_summary)
    return recursive_summarize(new_summaries, level + 1)

def main():
    CSV_directory_path = '/CSVData'
    csv_data = loadTextData(CSV_directory_path)
    print(csv_data)  # Prints all CSV row data as a list of strings
    openai.api_key = "YOUR_OPENAI_API_KEY"
    #data_chunks = load_data()
    #initial_summaries = [summarize_data(chunk, initial=True) for chunk in data_chunks]
    #final_summary = recursive_summarize(initial_summaries)
    #print("Final Summary:", final_summary)
if __name__ == "__main__":
    main()





