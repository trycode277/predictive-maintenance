FEATURE_COLUMNS = ["temperature_C", "vibration_mm_s", "rpm", "current_A"]

LEGACY_SENSOR_MAP = {
    "temp_1": "temperature_C",
    "vibration_1": "vibration_mm_s",
    "rpm_1": "rpm",
    "current_1": "current_A",
}


def preprocess(data):
    source = data.get("sensors", data)
    normalized = {}

    for legacy_key, canonical_key in LEGACY_SENSOR_MAP.items():
        if legacy_key in source:
            normalized[canonical_key] = source[legacy_key]

    for column in FEATURE_COLUMNS:
        if column in source:
            normalized[column] = source[column]

    if "status" in data:
        normalized["status"] = data["status"]
    elif "status" in source:
        normalized["status"] = source["status"]

    if "timestamp" in data:
        normalized["timestamp"] = data["timestamp"]

    return normalized
