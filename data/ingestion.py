# data/ingestion.py

import requests
import sseclient
import json

def get_live_api_data(machine_id):
    url = f"http://localhost:3000/stream/{machine_id}"
    
    response = requests.get(url, stream=True)
    client = sseclient.SSEClient(response)

    for event in client.events():
        data = json.loads(event.data)
        yield data