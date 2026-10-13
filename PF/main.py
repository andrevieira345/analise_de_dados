import requests
from fetch import API_KEY

params = {'api_key':API_KEY}
url = 'https://api.nasa.gov/neo/rest/v1/neo/browse'

"""
response = requests.get(url, params=params)
print(response.status_code)
"""

response = requests.get(url, params=params, timeout=30)
response.raise_for_status()
data = response.json()

print(data['page'])
for neo in data['near_earth_objects']:
    print(neo['name'], neo['is_potentially_hazardous_asteroid'])
