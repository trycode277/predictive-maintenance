#!/usr/bin/env python
"""
Quick API Integration Examples

Run these examples to test the API connection and understand the integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.api_client import APIClient
import json


def example_1_test_api_connection():
    """Example 1: Test if API is running"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Test API Connection")
    print("="*60)
    
    client = APIClient(base_url="http://localhost:3000")
    
    print("\n🔍 Checking API server health...")
    is_healthy = client.health_check()
    
    if is_healthy:
        print("✅ API Server is RUNNING on http://localhost:3000")
        return True
    else:
        print("❌ API Server is NOT running or unreachable")
        print("   Make sure your API server is started!")
        return False


def example_2_get_live_data():
    """Example 2: Fetch live data for one machine"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Get Live Data")
    print("="*60)
    
    client = APIClient(base_url="http://localhost:3000")
    
    print("\n📡 Fetching live data for CNC_01...")
    data = client.get_live_stream("CNC_01")
    
    if data:
        print("✅ SUCCESS! Live data received:")
        print(json.dumps(data, indent=2))
    else:
        print("❌ Failed to fetch live data")


def example_3_get_all_machines():
    """Example 3: Get list of available machines"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Get Available Machines")
    print("="*60)
    
    client = APIClient(base_url="http://localhost:3000")
    
    print("\n🏭 Fetching list of machines...")
    machines = client.get_all_machines()
    
    if machines:
        print(f"✅ Found {len(machines)} machines:")
        for machine in machines:
            print(f"   - {machine}")
    else:
        print("❌ Failed to fetch machine list")


def example_4_get_historical_data():
    """Example 4: Get historical data for ML training"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Get Historical Data")
    print("="*60)
    
    client = APIClient(base_url="http://localhost:3000")
    
    print("\n📊 Fetching 7 days of historical data for CNC_01...")
    history = client.get_historical_data("CNC_01", days=7)
    
    if history:
        print(f"✅ SUCCESS! Fetched {len(history)} records")
        print("\n📈 Sample records:")
        for i, record in enumerate(history[:3]):
            print(f"\n   Record {i+1}:")
            print(f"   - Timestamp: {record['timestamp']}")
            print(f"   - Temperature: {record['temperature_C']}°C")
            print(f"   - Vibration: {record['vibration_mm_s']} mm/s")
            print(f"   - RPM: {record['rpm']}")
            print(f"   - Current: {record['current_A']}A")
    else:
        print("❌ Failed to fetch historical data")


def example_5_loop_all_machines():
    """Example 5: Get live data for all machines in a loop"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Get Live Data for All Machines")
    print("="*60)
    
    client = APIClient(base_url="http://localhost:3000")
    
    print("\n🔄 Getting machines list...")
    machines = client.get_all_machines()
    
    if not machines:
        print("❌ Could not get machines list")
        return
    
    print(f"✅ Found {len(machines)} machines\n")
    
    print("📡 Fetching live data for all machines:")
    print("-" * 60)
    
    for machine_id in machines:
        data = client.get_live_stream(machine_id)
        if data:
            print(f"\n{machine_id}:")
            print(f"  Temperature: {data['temperature_C']}°C")
            print(f"  Vibration:   {data['vibration_mm_s']} mm/s")
            print(f"  RPM:         {data['rpm']}")
            print(f"  Current:     {data['current_A']}A")
            print(f"  Status:      {data['status']}")
        else:
            print(f"\n{machine_id}: ❌ Failed to fetch")


def example_6_continuous_stream():
    """Example 6: Continuous data streaming (like dashboard)"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Continuous Data Stream")
    print("="*60)
    print("\n📡 Streaming live data (Press Ctrl+C to stop)...")
    print("-" * 60)
    
    client = APIClient(base_url="http://localhost:3000")
    machines = client.get_all_machines()
    
    if not machines:
        print("❌ Could not get machines list")
        return
    
    try:
        import time
        count = 0
        while count < 5:  # Just show 5 iterations for demo
            print(f"\n⏰ Iteration {count + 1}:")
            
            for machine_id in machines:
                data = client.get_live_stream(machine_id)
                if data:
                    print(f"  {machine_id}: {data['temperature_C']}°C | {data['vibration_mm_s']} mm/s")
            
            count += 1
            if count < 5:
                print("  (Waiting 2 seconds...)")
                time.sleep(2)
        
        print("\n✅ Stream demo complete!")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stream stopped by user")


def example_7_compare_with_local():
    """Example 7: Compare API data with local simulated data"""
    print("\n" + "="*60)
    print("EXAMPLE 7: API vs Local Data Comparison")
    print("="*60)
    
    from data.ingestion import get_live_snapshot, MACHINE_PROFILES
    
    client = APIClient(base_url="http://localhost:3000")
    machines = ["CNC_01"]  # Just one for demo
    
    print("\n📊 Comparing API data vs Local simulation:")
    print("-" * 60)
    
    # Get from API
    print("\n🌐 From API Server:")
    api_data = client.get_live_stream(machines[0])
    if api_data:
        print(f"  {machines[0]}:")
        print(f"    Temperature: {api_data['temperature_C']}°C")
        print(f"    Vibration:   {api_data['vibration_mm_s']} mm/s")
        print(f"    Current:     {api_data['current_A']}A")
    else:
        print("  ❌ Failed to get API data")
    
    # Get from local
    print("\n💻 From Local Simulation:")
    local_data = get_live_snapshot(machines)
    if local_data:
        print(f"  {machines[0]}:")
        print(f"    Temperature: {local_data[0]['temperature_C']}°C")
        print(f"    Vibration:   {local_data[0]['vibration_mm_s']} mm/s")
        print(f"    Current:     {local_data[0]['current_A']}A")
    else:
        print("  ❌ Failed to get local data")
    
    print("\n💡 Both can be used depending on availability!")


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  🚀 API INTEGRATION EXAMPLES".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    # Example 1: Test connection
    api_available = example_1_test_api_connection()
    
    if not api_available:
        print("\n" + "!"*60)
        print("⚠️  API Server is not running!")
        print("!"*60)
        print("\n📝 To start the API server:")
        print("   1. Make sure you have an API server running on http://localhost:3000")
        print("   2. Or start your API server if it exists in your project")
        print("   3. Then run this script again")
        return
    
    # Run examples
    example_2_get_live_data()
    example_3_get_all_machines()
    example_4_get_historical_data()
    example_5_loop_all_machines()
    example_7_compare_with_local()
    
    print("\n" + "="*60)
    print("OPTIONAL: Continuous Stream Demo")
    print("="*60)
    print("\nTo see continuous streaming, uncomment example_6_continuous_stream()")
    print("in the main() function")
    
    print("\n" + "="*60)
    print("✅ All examples completed!")
    print("="*60)
    
    print("\n📚 Next Steps:")
    print("   1. Read API_INTEGRATION.md for full integration guide")
    print("   2. Choose integration method (hybrid, pure API, etc.)")
    print("   3. Modify dashboard/app.py to use APIClient")
    print("   4. Test with your actual API server")
    
    print("\n")


if __name__ == "__main__":
    # Uncomment to enable continuous stream example
    # example_6_continuous_stream()
    main()
