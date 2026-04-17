import requests

def get_history(machine_id):
    url = f"http://localhost:3000/history/{machine_id}"
    response = requests.get(url)
    return response.json()

def get_machines():
    url = "http://localhost:3000/machines"
    response = requests.get(url)
    return response.json()

def send_alert(machine_id, alert_payload):
    url = "http://localhost:3000/alerts"
    try:
        response = requests.post(url, json=alert_payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Alert POST failed: {e}")
        return None

