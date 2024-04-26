import openai

import os
import csv

def loadCSVData(root_dir):
    all_data = []
    # Walk through the directory
    for dirpath, dirnames, filenames in os.walk(root_dir):
        print(dirpath)
        for file in filenames:
            # Check if the file is a CSV
            if file.endswith('.csv'):
                file_path = os.path.join(dirpath, file)
                # Read the CSV file
                with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        # Convert row to string and append to the list
                        row_str = ','.join(row)
                        all_data.append(row_str)
    return all_data

# Usage

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
    csv_data = loadCSVData(CSV_directory_path)
    print(csv_data)  # Prints all CSV row data as a list of strings
    openai.api_key = "YOUR_OPENAI_API_KEY"
    #data_chunks = load_data()
    #initial_summaries = [summarize_data(chunk, initial=True) for chunk in data_chunks]
    #final_summary = recursive_summarize(initial_summaries)
    #print("Final Summary:", final_summary)
if __name__ == "__main__":
    main()





