#!/usr/bin/env python3
"""
Baseline Diagnostic Script
Shows what baseline values are being used for each machine
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.csv_loader import load_csv_data
from data.ingestion import MACHINE_PROFILES
from data.preprocessing import FEATURE_COLUMNS

MACHINE_IDS = list(MACHINE_PROFILES.keys())

def load_historical_frame(path):
    historical = pd.DataFrame(load_csv_data(path))
    rename_map = {
        "temp_1": "temperature_C",
        "vibration_1": "vibration_mm_s",
        "rpm_1": "rpm",
        "current_1": "current_A",
    }
    historical = historical.rename(columns=rename_map)

    if "machine_id" not in historical.columns:
        historical["machine_id"] = MACHINE_IDS[0]

    for column in FEATURE_COLUMNS:
        if column not in historical.columns:
            historical[column] = 0.0
        historical[column] = pd.to_numeric(historical[column], errors="coerce").fillna(0.0)

    return historical

def build_baselines(path):
    historical = load_historical_frame(path)
    global_std = {
        "temperature_C": max(float(historical["temperature_C"].std(ddof=0) or 0.0), 3.0),
        "vibration_mm_s": max(float(historical["vibration_mm_s"].std(ddof=0) or 0.0), 0.25),
        "rpm": max(float(historical["rpm"].std(ddof=0) or 0.0), 70.0),
        "current_A": max(float(historical["current_A"].std(ddof=0) or 0.0), 0.8),
    }
    baselines = {}

    for machine_id in MACHINE_IDS:
        machine_df = historical[historical["machine_id"] == machine_id]
        profile = MACHINE_PROFILES[machine_id]
        baselines[machine_id] = {}

        for column in FEATURE_COLUMNS:
            if machine_df.empty:
                mean_value = float(profile[column])
                std_value = global_std[column]
            else:
                mean_value = float(machine_df[column].mean())
                std_value = max(float(machine_df[column].std(ddof=0) or 0.0), global_std[column] * 0.45)

            baselines[machine_id][column] = {
                "mean": mean_value,
                "std": std_value,
            }

    return baselines, historical

def main():
    print("=" * 80)
    print("BASELINE DIAGNOSTIC - Why Alerts Aren't Triggering for Some Machines")
    print("=" * 80)
    
    baselines, historical = build_baselines("data/sample_data.csv")
    
    print("\n📊 HISTORICAL DATA SOURCE:")
    print("-" * 80)
    print(f"Total rows in sample_data.csv: {len(historical)}")
    print(f"Machines in sample_data.csv:")
    for machine in MACHINE_IDS:
        count = len(historical[historical["machine_id"] == machine])
        if count > 0:
            print(f"  ✅ {machine}: {count} rows")
        else:
            print(f"  ❌ {machine}: 0 rows (USING PROFILE DEFAULTS)")
    
    print("\n📈 BASELINE VALUES (Mean ± Std):")
    print("-" * 80)
    
    for machine_id in MACHINE_IDS:
        print(f"\n{machine_id}:")
        baseline = baselines[machine_id]
        profile = MACHINE_PROFILES[machine_id]
        
        # Check if this machine has historical data
        machine_data = historical[historical["machine_id"] == machine_id]
        has_data = len(machine_data) > 0
        status = "✅ FROM CSV DATA" if has_data else "❌ FROM PROFILE DEFAULTS"
        print(f"  Status: {status}")
        
        for column in FEATURE_COLUMNS:
            mean = baseline[column]["mean"]
            std = baseline[column]["std"]
            profile_val = profile[column]
            print(f"    {column:20s}: {mean:7.2f} ± {std:5.2f}  (Profile: {profile_val})")
    
    print("\n⚠️ ALERT THRESHOLD ANALYSIS:")
    print("-" * 80)
    print("\nTemperature thresholds for CRITICAL alert:")
    print("  Risk score >= 80 = CRITICAL")
    print("  Temperature trigger = max(88°C, baseline_mean + baseline_std * 2.2)")
    print()
    
    for machine_id in MACHINE_IDS:
        baseline = baselines[machine_id]
        temp_mean = baseline["temperature_C"]["mean"]
        temp_std = baseline["temperature_C"]["std"]
        
        # Calculate the temperature threshold for critical
        threshold = max(88.0, temp_mean + temp_std * 2.2)
        
        print(f"{machine_id}:")
        print(f"  Baseline mean:    {temp_mean:.2f}°C")
        print(f"  Baseline std:     {temp_std:.2f}°C")
        print(f"  Critical threshold: {threshold:.2f}°C")
        print(f"  Distance from baseline: {(threshold - temp_mean):.2f}°C")
        print()
    
    print("\n💡 SOLUTION:")
    print("-" * 80)
    print("The sample_data.csv only contains CNC_01 data.")
    print("CNC_02, PUMP_03, and CONVEYOR_04 use PROFILE defaults as baselines.")
    print("\nThis means:")
    print("  ✅ CNC_01 has proper training data → Alerts work correctly")
    print("  ❌ Other machines have flat baselines → Alerts harder to trigger")
    print("\nFIX: Generate synthetic training data for all 4 machines and add to CSV")

if __name__ == "__main__":
    main()
