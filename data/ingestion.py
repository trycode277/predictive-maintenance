import json
import random
import time
from datetime import datetime, timezone


MACHINE_PROFILES = {
    "CNC_01": {
        "temperature_C": 67.0,
        "vibration_mm_s": 1.05,
        "rpm": 1450.0,
        "current_A": 11.8,
    },
    "CNC_02": {
        "temperature_C": 70.0,
        "vibration_mm_s": 1.15,
        "rpm": 1510.0,
        "current_A": 12.6,
    },
    "PRESS_01": {
        "temperature_C": 74.0,
        "vibration_mm_s": 1.35,
        "rpm": 1385.0,
        "current_A": 13.8,
    },
    "LATHE_01": {
        "temperature_C": 69.0,
        "vibration_mm_s": 0.95,
        "rpm": 1565.0,
        "current_A": 11.2,
    },
}

FAULT_LIBRARY = {
    "thermal_drift": {
        "duration": (4, 8),
        "temperature_C": (1.6, 3.1),
        "current_A": (0.2, 1.0),
        "rpm": (-18.0, 12.0),
        "status": "warning",
    },
    "bearing_wear": {
        "duration": (4, 7),
        "temperature_C": (0.5, 1.6),
        "vibration_mm_s": (0.35, 0.85),
        "current_A": (0.1, 0.6),
        "status": "warning",
    },
    "motor_overload": {
        "duration": (3, 6),
        "temperature_C": (0.8, 1.9),
        "current_A": (0.9, 2.2),
        "rpm": (-40.0, 8.0),
        "status": "warning",
    },
    "compound_fault": {
        "duration": (3, 6),
        "temperature_C": (2.2, 4.6),
        "vibration_mm_s": (0.5, 1.0),
        "current_A": (0.9, 2.0),
        "status": "fault",
    },
}

_MACHINE_STATE = {
    machine_id: {
        "temperature_offset": 0.0,
        "vibration_offset": 0.0,
        "rpm_offset": 0.0,
        "current_offset": 0.0,
        "fault_mode": None,
        "fault_ticks_remaining": 0,
    }
    for machine_id in MACHINE_PROFILES
}


def _utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _bounded(value, lower, upper):
    return max(lower, min(upper, value))


def _start_fault_if_needed(state):
    if state["fault_ticks_remaining"] > 0:
        return

    if random.random() < 0.14:
        fault_mode = random.choices(
            population=list(FAULT_LIBRARY),
            weights=[0.35, 0.3, 0.2, 0.15],
            k=1,
        )[0]
        duration_low, duration_high = FAULT_LIBRARY[fault_mode]["duration"]
        state["fault_mode"] = fault_mode
        state["fault_ticks_remaining"] = random.randint(duration_low, duration_high)
    else:
        state["fault_mode"] = None


def _update_offsets(machine_id):
    state = _MACHINE_STATE[machine_id]

    state["temperature_offset"] = _bounded(
        state["temperature_offset"] * 0.82 + random.uniform(-0.9, 0.9),
        -5.0,
        18.0,
    )
    state["vibration_offset"] = _bounded(
        state["vibration_offset"] * 0.78 + random.uniform(-0.18, 0.18),
        -0.5,
        1.6,
    )
    state["rpm_offset"] = _bounded(
        state["rpm_offset"] * 0.76 + random.uniform(-28.0, 28.0),
        -180.0,
        120.0,
    )
    state["current_offset"] = _bounded(
        state["current_offset"] * 0.8 + random.uniform(-0.35, 0.35),
        -1.2,
        4.5,
    )

    _start_fault_if_needed(state)

    if state["fault_ticks_remaining"] > 0 and state["fault_mode"]:
        fault = FAULT_LIBRARY[state["fault_mode"]]
        state["temperature_offset"] = _bounded(
            state["temperature_offset"] + random.uniform(*fault.get("temperature_C", (0.0, 0.0))),
            -5.0,
            28.0,
        )
        state["vibration_offset"] = _bounded(
            state["vibration_offset"] + random.uniform(*fault.get("vibration_mm_s", (0.0, 0.0))),
            -0.5,
            2.4,
        )
        state["rpm_offset"] = _bounded(
            state["rpm_offset"] + random.uniform(*fault.get("rpm", (0.0, 0.0))),
            -250.0,
            160.0,
        )
        state["current_offset"] = _bounded(
            state["current_offset"] + random.uniform(*fault.get("current_A", (0.0, 0.0))),
            -1.2,
            5.8,
        )
        state["fault_ticks_remaining"] -= 1
        if state["fault_ticks_remaining"] <= 0:
            state["fault_mode"] = None

    return state


def _status_for_reading(temperature_c, vibration_mm_s, current_a, fault_mode):
    if fault_mode == "compound_fault":
        return "fault"
    if temperature_c > 96 or vibration_mm_s > 2.9 or current_a > 17.8:
        return "fault"
    if fault_mode or temperature_c > 82 or vibration_mm_s > 1.95 or current_a > 15.7:
        return "warning"
    return "running"


def generate_live_reading(machine_id):
    profile = MACHINE_PROFILES[machine_id]
    state = _update_offsets(machine_id)

    temperature_c = round(
        profile["temperature_C"] + state["temperature_offset"] + random.uniform(-0.8, 0.8),
        2,
    )
    vibration_mm_s = round(
        max(0.2, profile["vibration_mm_s"] + state["vibration_offset"] + random.uniform(-0.08, 0.08)),
        2,
    )
    rpm = round(profile["rpm"] + state["rpm_offset"] + random.uniform(-12.0, 12.0), 2)
    current_a = round(
        max(5.0, profile["current_A"] + state["current_offset"] + random.uniform(-0.18, 0.18)),
        2,
    )

    status = _status_for_reading(temperature_c, vibration_mm_s, current_a, state["fault_mode"])

    return {
        "machine_id": machine_id,
        "timestamp": _utc_timestamp(),
        "temperature_C": temperature_c,
        "vibration_mm_s": vibration_mm_s,
        "rpm": rpm,
        "current_A": current_a,
        "status": status,
    }


def get_live_snapshot(machine_ids=None, dropout_probability=0.08):
    machine_ids = machine_ids or list(MACHINE_PROFILES)
    snapshot = []

    for machine_id in machine_ids:
        if random.random() < dropout_probability:
            continue
        snapshot.append(generate_live_reading(machine_id))

    return snapshot


def get_live_data(machine_id):
    while True:
        yield json.dumps(generate_live_reading(machine_id))
        time.sleep(1)
