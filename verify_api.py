#!/usr/bin/env python3
"""
API Verification Script
Tests connection to http://localhost:3000 and verifies data reception
"""

import sys
import os

# Add parent directory to path so we can import local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.api_client import APIClient
import json

def test_api_connection():
    """Test API connection and data reception"""
    
    print("=" * 70)
    print("API CLIENT VERIFICATION TEST")
    print("=" * 70)
    
    # Create client
    client = APIClient(base_url="http://localhost:3000")
    print(f"\n✓ API Client created")
    print(f"  Base URL: {client.base_url}")
    print(f"  Timeout: {client.timeout}s")
    
    # Test 1: Health Check
    print("\n" + "=" * 70)
    print("TEST 1: HEALTH CHECK")
    print("=" * 70)
    
    health = client.health_check()
    if health:
        print("✅ API Server is HEALTHY and reachable")
    else:
        print("❌ API Server is NOT REACHABLE")
        print("   Make sure server is running on http://localhost:3000")
        return False
    
    # Test 2: Get Machines List
    print("\n" + "=" * 70)
    print("TEST 2: GET AVAILABLE MACHINES")
    print("=" * 70)
    
    machines = client.get_all_machines()
    if machines:
        print(f"✅ Found {len(machines)} machines:")
        for i, machine_id in enumerate(machines, 1):
            print(f"   {i}. {machine_id}")
    else:
        print("⚠️  Could not retrieve machine list")
        machines = ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"]  # Fallback
        print(f"   Using default machines: {machines}")
    
    # Test 3: Get Live Stream Data from Each Machine
    print("\n" + "=" * 70)
    print("TEST 3: LIVE STREAM DATA FROM EACH MACHINE")
    print("=" * 70)
    
    success_count = 0
    for machine_id in machines:
        print(f"\n  Fetching data from {machine_id}...")
        
        try:
            reading = client.get_live_stream(machine_id)
            
            if reading:
                print(f"    ✅ Data received")
                print(f"       Machine ID: {reading.get('machine_id')}")
                print(f"       Temperature: {reading.get('temperature_C')}°C")
                print(f"       Vibration: {reading.get('vibration_mm_s')} mm/s")
                print(f"       RPM: {reading.get('rpm')}")
                print(f"       Current: {reading.get('current_A')}A")
                print(f"       Timestamp: {reading.get('timestamp')}")
                print(f"       Status: {reading.get('status')}")
                success_count += 1
            else:
                print(f"    ❌ No data returned (reading is None)")
                
        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
    
    print(f"\n  Summary: {success_count}/{len(machines)} machines received data")
    
    # Test 4: Verify Data Format
    print("\n" + "=" * 70)
    print("TEST 4: DATA FORMAT VALIDATION")
    print("=" * 70)
    
    if machines:
        first_machine = machines[0]
        print(f"\n  Testing data format from {first_machine}...")
        
        reading = client.get_live_stream(first_machine)
        if reading:
            # Check required fields
            required_fields = ["machine_id", "temperature_C", "vibration_mm_s", "rpm", "current_A", "timestamp"]
            print(f"\n  Required fields:")
            all_present = True
            for field in required_fields:
                present = field in reading
                status = "✅" if present else "❌"
                print(f"    {status} {field}: {reading.get(field, 'MISSING')}")
                if not present:
                    all_present = False
            
            if all_present:
                print(f"\n    ✅ All required fields present")
            else:
                print(f"\n    ❌ Some required fields missing")
        else:
            print(f"  ❌ Could not get sample data")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if health and success_count > 0:
        print("✅ API CONNECTION VERIFIED")
        print(f"✅ DATA RECEPTION WORKING ({success_count}/{len(machines)} machines)")
        print("✅ SYSTEM READY FOR DASHBOARD")
        return True
    elif health:
        print("⚠️  API SERVER REACHABLE but NO DATA from machines")
        print("   Check machine endpoint: /stream/{machine_id}")
    else:
        print("❌ API SERVER NOT REACHABLE")
        print("   Start server: node api-server.js or python api_server.py")
        return False

if __name__ == "__main__":
    success = test_api_connection()
    sys.exit(0 if success else 1)
