import requests

# Test /api/students endpoint
response = requests.get('http://localhost:5000/api/students?page=1&per_page=5')
print('Status:', response.status_code)
print('Response:', response.json())