import json
import csv
import pandas as pd

def json_to_excel(jsonl_file, excel_file):
    file = open(jsonl_file, "r")
    lines = file.readlines()
    file.close()

    df = None

    for line in lines:
        first_line = line.replace('\n', '')
        first_line = first_line.replace('\'', '"')
        json_data = json.loads(first_line)

        if (df is None):
            df = pd.DataFrame.from_dict(pd.json_normalize(json_data), orient='columns')
        else:
            df2 = pd.DataFrame.from_dict(pd.json_normalize(json_data), orient='columns')
            df = pd.concat([df, df2], ignore_index = True)
    
    # Convert CSV to Excel
    df.to_excel(excel_file, index=False)

# Example usage
# json_to_excel('synch.txt', 'sync_payload_wide.xlsx')
# json_to_excel('asynch.txt', 'async_payload_wide.xlsx')
json_to_excel('test.txt', 'differential-images-diff.xlsx')
# json_to_excel('resolution-vs-time-1080p.txt', 'resolution-vs-time-1080p.xlsx')
# json_to_excel('15ms_TO-10.txt', '15ms_TO-10.xlsx')
# json_to_excel('15ms_TO-11.txt', '15ms_TO-11.xlsx')