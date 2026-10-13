import requests
from fetch import API_KEY

params = {'api_key':API_KEY}
url = 'https://api.nasa.gov/neo/rest/v1/neo/browse'

response = requests.get(url, params=params)
print(response.status_code)
