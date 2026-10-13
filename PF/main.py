import requests
from fetch import API_KEY

params = {'api_key':API_KEY}
url = 'https://api.nasa.gov/neo/rest/v1/neo/browse'

# Test Response
"""
response = requests.get(url, params=params)
print(response.status_code)
"""
# Bigger test response
"""
response = requests.get(url, params=params, timeout=30)
response.raise_for_status()
print(f"Requests remaining: {response.headers.get('X-RateLimit-Remaining')}")
data = response.json()

print(data['page'])
for neo in data['near_earth_objects']:
    print(neo['name'], neo['is_potentially_hazardous_asteroid'])
"""

# Data requests from API saved in JSON on data folder, skips already downloaded data.

response = requests.get(url, params=params)


