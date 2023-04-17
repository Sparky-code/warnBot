import requests

data = { "status" : "testing 1 2, 1 2"}

url = "%s/api/v1/statuses" % (MASTADON_HOST)
r = requests.posts(url,
        data=data,
        headers={'Authorization': 'Bearer %s' (MASTADON_TOKEN)})
json_data = r.json()