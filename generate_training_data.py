#!/usr/bin/env python3
"""
Generate Historical Training Data for All Machines
Creates synthetic historical data that maintains realistic patterns for each machine
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ingestion import MACHINE_PROFILES

def generate_machine_history(machine_id, baseline, start_temp=None, num_records=100):
    """
    Generate realistic historical data for a machine
    
    Args:
        machine_id: Machine ID
        baseline: Profile values (temperature_C, vibration_mm_s, rpm, current_A)
        start_temp: Starting temperature (defaults to baseline)
        num_records: Number of records to generate
        
    Returns:
        List of sensor reading dicts
    """
    if start_temp is None:
        start_temp = baseline["temperature_C"] - 5
    
    records = []
    timestamp = datetime(2026, 1, 1, 0, 0, 0)
    
    # Current values (will drift during simulation)
    current_temp = start_temp
    current_vibration = baseline["vibration_mm_s"] * 0.8
    current_rpm = baseline["rpm"] * 0.95
    current_current = baseline["current_A"] * 0.9
    
    for i in range(num_records):
        # Add realistic drift and noise
        temp_change = random.uniform(-0.5, 1.2)  # Gradual warming
        vibration_change = random.uniform(-0.1, 0.15)
        rpm_change = random.uniform(-20, 30)
        current_change = random.uniform(-0.15, 0.25)
        
        current_temp = min(current_temp + temp_change, baseline["temperature_C"] + 8)
        current_vibration = max(min(current_vibration + vibration_change, baseline["vibration_mm_s"] + 0.5), baseline["vibration_mm_s"] * 0.7)
        current_rpm = baseline["rpm"] + random.uniform(-50, 50)
        current_current = baseline["current_A"] + random.uniform(-0.5, 0.8)
        
        records.append({
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "machine_id": machine_id,
            "temperature_C": round(current_temp, 2),
            "vibration_mm_s": round(current_vibration, 2),
            "rpm": round(current_rpm, 0),
            "current_A": round(current_current, 2),
        })
        
        timestamp += timedelta(minutes=1)
    
    return records

def main():
    print("=" * 80)
    print("GENERATING TRAINING DATA FOR ALL 4 MACHINES")
    print("=" * 80)
    
    # Load existing sample data
    csv_path = "data/sample_data.csv"
    df_existing = pd.read_csv(csv_path)
    
    print(f"\n📂 Existing data: {len(df_existing)} rows")
    print(f"   Machines: {df_existing['machine_id'].unique().tolist()}")
    
    # Generate new data for each machine
    all_records = []
    
    for machine_id, baseline in MACHINE_PROFILES.items():
        print(f"\n📊 Generating {machine_id}...")
        
        # Generate 100 realistic samples for each machine
        records = generate_machine_history(machine_id, baseline, num_records=100)
        all_records.extend(records)
        
        print(f"   ✅ Generated {len(records)} records")
        print(f"      Temp range: {min(r['temperature_C'] for r in records):.1f}°C - {max(r['temperature_C'] for r in records):.1f}°C")
        print(f"      Vibration range: {min(r['vibration_mm_s'] for r in records):.2f} - {max(r['vibration_mm_s'] for r in records):.2f} mm/s")
        print(f"      RPM range: {min(r['rpm'] for r in records):.0f} - {max(r['rpm'] for r in records):.0f}")
        print(f"      Current range: {min(r['current_A'] for r in records):.2f}A - {max(r['current_A'] for r in records):.2f}A")
    
    # Create new dataframe with all records
    df_new = pd.DataFrame(all_records)
    
    # Save to CSV
    df_new.to_csv(csv_path, index=False)
    
    print(f"\n✅ TRAINING DATA COMPLETE")
    print(f"   Total records: {len(df_new)}")
    print(f"   Machines: {df_new['machine_id'].unique().tolist()}")
    print(f"   File: {csv_path}")
    print(f"\n💡 Now each machine has proper historical data for baseline training!")

if __name__ == "__main__":
    main()
