import requests

url = "https://api.ayrshare.com/api/post"
headers = {
"Authorization": "Bearer 51B2019D-8F244E99-B1CAF823-3BD8994F",
"Content-Type": "application/json"
}
data = {
"post": "Good Morning", #Mandatory
"platforms": ["linkedin", "facebook"],
"mediaUrls": ["https://img.ayrshare.com/012/gb.jpg"]
}

response = requests.post(url, json=data, headers=headers)
print(response.json())