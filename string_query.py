import requests
def string_query(queryString,variables,headers):

    url = 'https://api.start.gg/gql/alpha'

    payload = {
    "query": queryString,
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

