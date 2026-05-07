import requests
import os

zone_id = os.getenv("CLOUDFLARE_ZONE_ID")
token = os.getenv("CLOUDFLARE_API_TOKEN")

url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

data = {
    "purge_everything": True
}

response = requests.post(url, headers=headers, json=data)

print(response.status_code)
print(response.json())
