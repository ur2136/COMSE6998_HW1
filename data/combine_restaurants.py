"""
    Combines all the data in the [cuisine].txt files to a single final.txt.
    The [cuisine].txt files are included in the ./restaurants directory. 
    Check for any duplicates and drop rows as necessary. 
    Finally verify that there remain at least 5000 restaurants after dropping
    all the duplicates. 
"""
import os
import json
import pandas as pd

# collect all the [cuisine].txt files
all_files = os.listdir("./restaurants/")
all_files = [a for a in all_files if a[-4:] == '.txt']
all_files = sorted(all_files)

df = pd.DataFrame()
for af in all_files: 
    df_ = pd.read_json("./restaurants/" + af)
    df = pd.concat([df, df_])

# print(df.head())
# print(len(df))
df.set_index('id')
df.drop_duplicates(subset='id', keep='first', inplace=True)
# print(any(df["id"].duplicated())) # check for duplicates
# print(len(df)) # check that we have at least 5000 

result = df.to_json(orient="records") # records is the correct one
parsed = json.loads(result)
with open('final.txt', 'w') as outfile: 
    json.dump(parsed, outfile)