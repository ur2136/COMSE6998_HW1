"""
    Code for pulling the data of restaurants associated with a specific cuisine in Manhattan.
    Generates [cuisine].txt (i.e. italian.txt, chinese.txt).  
    Several tricks were used to overcome the limitations of the Yelp API: 
        1. Yelp API only returns up to 50 restaurants per query -- used offset parameter to 
           retrieve results beyond the initial 50
        2. Yelp API only returns a limited number of restaurants (up to 240) in Manhattan 
           even if the total number in Manhattan is greater -- used different locations in 
           Manhattan with a radius of 1000 meters around each to retrieve more than 240
        3. Yelp API may classify the same restaurant under multiple different cuisine categories
           -- this leads to possible duplicates; some cleaning was necessary after the data 
           collection to remove the duplicates
"""
import json
import pandas as pd
import requests

df = pd.DataFrame()

url = "https://api.yelp.com/v3/businesses/search"
key = "3DK3I8tlbBdiZKMchzMheF2zQe9wmLb1TIonEWlpAKUr-v7JNuOuAs78DRl1NLitrPSWLxAcjqRHAyVFR2JwQzG1TREc88aJB-Ji3e-2-9jReK_s8G9d68ElJ6FUYXYx"
headers = {
    'Authorization': 'Bearer %s' % key
}

latitudes = [(40.824447,-73.947673), (40.806777,-73.961267), (40.789105,-73.946986), (40.786001,-73.977814),
             (40.770412,-73.959466), (40.768322,-73.994636), (40.755069,-73.974572), (40.749102,-74.002020),
             (40.736876,-73.980047), (40.730112,-74.006826), (40.718119,-73.986397), (40.709556,-74.011633)]
latitudes, longitudes = [a[0] for a in latitudes], [a[1] for a in latitudes]

SEARCH_TERM = "italian"
SEARCH_LIMIT = 50 # specified by the Yelp API
OFFSET = 0

for lat, long in zip(latitudes, longitudes): 
    parameters = {'latitude': lat, 
                  'longitude': long, 
                  'radius': 1000, 
                  'term': SEARCH_TERM,
                  'limit': SEARCH_LIMIT, 
                  'offset': OFFSET}
    response = requests.get(url, headers=headers, params=parameters)
    data = response.json()
    df_ = pd.json_normalize(data['businesses'])
    df = pd.concat([df, df_])

    while data['total'] > 50 * (OFFSET+1): 
        OFFSET += 1
        parameters = {
            "latitude": lat, 
            "longitude": long, 
            "radius": 1000, 
            "term": SEARCH_TERM, 
            "limit": SEARCH_LIMIT, 
            "offset": OFFSET
        }
        response = requests.get(url, headers=headers, params=parameters)
        data = response.json()
        df_ = pd.json_normalize(data['businesses'])
        df = pd.concat([df, df_])

df.set_index('id')
df.drop_duplicates(subset ="id", keep = 'first', inplace = True)
# print(any(df["id"].duplicated()))
# print(dd.head())
result = df.to_json(orient="records")
parsed = json.loads(result)
with open('italian.txt', 'w') as outfile: 
    json.dump(parsed, outfile)