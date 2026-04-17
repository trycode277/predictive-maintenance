#!/usr/bin/env python
"""
🔥 Real-time Parallel Stream Example

Listen to all 4 machines simultaneously using SSE streams and process with AI Agent

Architecture:
    CNC_01 ─┐
    CNC_02 ─┼──→ AI Agent → Alert
    PUMP_03 ─┤
    CONVEYOR─┘

Run this to see all 4 streams working together!
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.api_stream_client import StreamAPIClient
from agent.decision_agent import DecisionAgent
from models.isolation_forest import AnomalyModel
import time
import json


class RealTimeAnomalyDetector:
    """
    Real-time anomaly detection with AI decision making
    Listens to all machine streams and processes with agent
    """
    
    def __init__(self, api_url: str = "http://localhost:3000"):
        self.client = StreamAPIClient(base_url=api_url)
        
        # Initialize AI Agent
        try:
            self.model = AnomalyModel(contamination=0.1)
            self.model.train_with_isolation_forest()
            self.agent = DecisionAgent(self.model)
            print("✅ AI Agent initialized")
        except Exception as e:
            print(f"⚠️  Could not load AI Agent: {e}")
            self.agent = None
        
        self.reading_count = 0
        self.alert_count = 0
    
    def on_machine_data(self, machine_id: str, data: dict):
        """
        🔥 Called whenever new data arrives from ANY machine
        
        This is where the AI decision making happens!
        """
        self.reading_count += 1
        
        print(f"\n📊 [{self.reading_count}] {machine_id}")
        print(f"   Temperature: {data['temperature_C']:.1f}°C")
        print(f"   Vibration:   {data['vibration_mm_s']:.2f} mm/s")
        print(f"   RPM:         {data['rpm']:.0f}")
        print(f"   Current:     {data['current_A']:.1f}A")
        
        # 🤖 Process with AI Agent
        if self.agent:
            try:
                result = self.agent.analyze(data, machine_id)
                
                print(f"   🧠 AI Decision: {result['decision']}")
                print(f"   📌 Recommendation: {result['recommendation']}")
                
                # Send alert if CRITICAL or WARNING
                if result['decision'] in ['CRITICAL', 'WARNING']:
                    self.alert_count += 1
                    print(f"   🚨 ALERT #{self.alert_count}: {result['action']}")
                    
                    # Send to API
                    self.client.send_alert(
                        machine_id=machine_id,
                        alert_type=result['decision'],
                        message=result['recommendation'],
                        data=data
                    )
            
            except Exception as e:
                print(f"   ⚠️  Agent error: {e}")
    
    def on_error(self, machine_id: str, error_msg: str):
        """Called when stream error occurs"""
        print(f"\n❌ Error in {machine_id}: {error_msg}")
    
    def start(self, machines: list = None):
        """Start listening to all machines"""
        if machines is None:
            machines = ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"]
        
        print("\n" + "="*60)
        print("🚀 REAL-TIME ANOMALY DETECTION")
        print("="*60)
        
        # Test API connection
        print("\n🔍 Testing API connection...")
        if not self.client.health_check():
            print("❌ API is not running!")
            print("   Start your API server on localhost:3000")
            return
        
        print(f"✅ API is healthy\n")
        
        # Start parallel listeners
        print(f"📡 Connecting to {len(machines)} machines...")
        print(f"   {', '.join(machines)}\n")
        
        threads = self.client.listen_all_machines(
            machine_ids=machines,
            callback=self.on_machine_data,
            error_callback=self.on_error
        )
        
        print(f"✅ All {len(threads)} streams are now listening!\n")
        print("Waiting for data... (press Ctrl+C to stop)\n")
        
        try:
            # Keep running until interrupted
            while True:
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping listeners...")
            self.client.stop_listening()
            
            print("\n" + "="*60)
            print("📊 SUMMARY")
            print("="*60)
            print(f"Total readings: {self.reading_count}")
            print(f"Alerts sent:    {self.alert_count}")
            print(f"Rate:           {self.reading_count / max(self.alert_count, 1):.1f} readings per alert")
            print("="*60 + "\n")


def example_1_test_streams():
    """Example 1: Test if all streams are working"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Test All Streams")
    print("="*60)
    
    client = StreamAPIClient(base_url="http://localhost:3000")
    
    print("\n🔍 Checking API health...")
    if not client.health_check():
        print("❌ API is not running!")
        return
    
    print("✅ API is healthy\n")
    
    machines = ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"]
    reading_count = [0]  # Use list for closure
    
    def on_data(machine_id, data):
        reading_count[0] += 1
        print(f"[{reading_count[0]:3d}] {machine_id}: {data['temperature_C']}°C | {data['vibration_mm_s']:.2f} mm/s")
        
        # Stop after 10 readings per machine (40 total)
        if reading_count[0] >= 40:
            raise KeyboardInterrupt()
    
    print("📡 Starting parallel streams...")
    try:
        client.listen_all_machines(machines, on_data)
        
        # Keep running
        import time
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n✅ Test complete!")
        client.stop_listening()


def example_2_with_ai_agent():
    """Example 2: Stream data + AI decision making"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Streams + AI Agent")
    print("="*60)
    
    detector = RealTimeAnomalyDetector()
    detector.start(machines=["CNC_01", "CNC_02"])  # Just 2 machines for demo


def example_3_show_architecture():
    """Example 3: Show the architecture"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Architecture Explanation")
    print("="*60)
    
    architecture = """
    🏭 PHYSICAL MACHINES
    ├─ CNC_01 (Industrial machine 1)
    ├─ CNC_02 (Industrial machine 2)
    ├─ PUMP_03 (Pump system)
    └─ CONVEYOR_04 (Conveyor line)
    
    📡 API SERVER (localhost:3000)
    ├─ /stream/CNC_01 (SSE stream)
    ├─ /stream/CNC_02 (SSE stream)
    ├─ /stream/PUMP_03 (SSE stream)
    ├─ /stream/CONVEYOR_04 (SSE stream)
    └─ /alert (receive alerts)
    
    🧵 PYTHON THREADS (Parallel Processing)
    ├─ Thread 1 → Listen CNC_01
    ├─ Thread 2 → Listen CNC_02
    ├─ Thread 3 → Listen PUMP_03
    └─ Thread 4 → Listen CONVEYOR_04
    
    🤖 AI AGENT (Per-Machine Processing)
    ├─ Anomaly Detection (ML: Isolation Forest)
    ├─ Rule Engine (8 thresholds)
    ├─ Decision Making (CRITICAL/WARNING/WATCH/NORMAL)
    └─ Action Taking (Alerts, Shutdown, Monitor)
    
    📊 RESULTS
    ├─ Color-coded decisions
    ├─ Real-time recommendations
    ├─ Automatic alerts
    └─ Historical logging
    
    KEY INSIGHT:
    All 4 streams run simultaneously (parallel threads)
    Each gets processed by the same AI agent
    Decisions made in real-time
    Alerts sent back immediately
    """
    
    print(architecture)


def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  🔥 PARALLEL SSE STREAM EXAMPLES".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    print("\nChoose an example:")
    print("  1) Test all 4 streams")
    print("  2) Streams + AI Agent")
    print("  3) Show architecture")
    print("  0) Run full real-time detector")
    
    try:
        choice = input("\nEnter choice (0-3): ").strip()
        
        if choice == "1":
            example_1_test_streams()
        elif choice == "2":
            example_2_with_ai_agent()
        elif choice == "3":
            example_3_show_architecture()
        elif choice == "0":
            detector = RealTimeAnomalyDetector()
            detector.start()
        else:
            print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\n\n✅ Stopped!")


if __name__ == "__main__":
    main()
