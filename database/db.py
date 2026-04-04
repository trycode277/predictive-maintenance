import json
import os
from datetime import datetime, timezone

SENSOR_FILE_PATH = "database/sensor_data.json"
ALERT_FILE_PATH = "database/alerts.json"


def _utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _ensure_file(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as file:
            json.dump([], file)


def _load_json(path):
    _ensure_file(path)
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _save_json(path, payload):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4)


def init_db():
    _ensure_file(SENSOR_FILE_PATH)
    _ensure_file(ALERT_FILE_PATH)


def save_data(machine_id, reading):
    data = _load_json(SENSOR_FILE_PATH)

    sensor_payload = {
        key: value
        for key, value in reading.items()
        if key not in {"timestamp"}
    }

    new_entry = {
        "machine_id": machine_id,
        "timestamp": reading.get("timestamp", _utc_timestamp()),
        "status": reading.get("status", "unknown"),
        "sensors": sensor_payload,
    }

    data.append(new_entry)
    if len(data) > 1000:
        data = data[-1000:]

    _save_json(SENSOR_FILE_PATH, data)


def save_alert(alert_payload):
    alerts = _load_json(ALERT_FILE_PATH)
    alerts.append(alert_payload)
    if len(alerts) > 300:
        alerts = alerts[-300:]
    _save_json(ALERT_FILE_PATH, alerts)


def load_alerts(limit=50):
    alerts = _load_json(ALERT_FILE_PATH)
    return list(reversed(alerts[-limit:]))
