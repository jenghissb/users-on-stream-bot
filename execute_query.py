import os
import requests
def excecute_query(queryFile,variables,headers):

    url = 'https://api.start.gg/gql/alpha'

    if not os.path.exists(queryFile):
        file_path = os.path.abspath(os.path.dirname(__file__))
        queryFile = os.path.join(file_path,"queries",queryFile)


    with open(queryFile) as infile:
        query_string = infile.read()

    payload = {
    "query": query_string,
    "variables": variables
    }

    response = requests.post(url, json=payload, headers=headers)

    try:
    # Extract the data from the response
        data = response.json()
        return data

    except:
        print(response)
        return None

