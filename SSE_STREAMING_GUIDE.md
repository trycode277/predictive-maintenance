# 🔥 Parallel SSE Stream Architecture Guide

## Key Insight

Your API uses **Server-Sent Events (SSE)**, not REST polling.

### ❌ Wrong Approach
```python
# This only gets ONE machine ONE time
data = client.get_live_stream("CNC_01")
```

### ✅ Correct Approach
```python
# Listen to ALL 4 machines continuously (parallel)
client.listen_all_machines(
    ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"],
    callback=on_data
)
```

---

## Architecture Diagram

```
🏭 REAL WORLD
CNC_01      CNC_02      PUMP_03     CONVEYOR_04
  │           │           │            │
  └───────────┴───────────┴────────────┘
              │
        API SERVER
      localhost:3000
              │
        ┌─────┴────────┐
        │              │
    /stream/        /alert
    CNC_01-04        (POST)
    (SSE)
        │
        ├──→ [Thread 1] ──→ CNC_01 Data
        ├──→ [Thread 2] ──→ CNC_02 Data
        ├──→ [Thread 3] ──→ PUMP_03 Data
        └──→ [Thread 4] ──→ CONVEYOR Data
              │
              └──→ AI Agent (shared)
                     │
                     ├─ ML Anomaly Detection
                     ├─ Rule Engine
                     └─ Decision Making
                          │
                          └──→ POST /alert (if needed)
```

---

## What is SSE (Server-Sent Events)?

### REST API (What You Knew)
```
Client: GET /data
Server: {"data": "value"}
        (connection closes)

Client must POLL repeatedly:
- Every 1 second: GET /data
- Every 1 second: GET /data
- Every 1 second: GET /data
```

### SSE Streaming (What You Have Now)
```
Client: GET /stream/CNC_01 (keep connection open)
Server: data: {"machine_id":"CNC_01",...}
Server: data: {"machine_id":"CNC_01",...}
Server: data: {"machine_id":"CNC_01",...}
        (connection stays open)
```

**Benefit:** No polling needed! Data pushed automatically when available.

---

## The 4 Machines

| Machine | Type | Purpose |
|---------|------|---------|
| **CNC_01** | Industrial CNC | Metal cutting/shaping |
| **CNC_02** | Industrial CNC | Metal cutting/shaping |
| **PUMP_03** | Centrifugal pump | Fluid movement |
| **CONVEYOR_04** | Conveyor system | Product transport |

Each has its own stream endpoint:
```
/stream/CNC_01
/stream/CNC_02
/stream/PUMP_03
/stream/CONVEYOR_04
```

---

## Threading for Parallel Processing

### Why Threading?

If you listen to machines sequentially:
```python
# ❌ WRONG - Takes 4x longer
listen_to_machine("CNC_01")    # Wait 10 seconds
listen_to_machine("CNC_02")    # Wait 10 seconds
listen_to_machine("PUMP_03")   # Wait 10 seconds
listen_to_machine("CONVEYOR") # Wait 10 seconds
# Total: 40 seconds to get data from all 4!
```

If you listen in parallel (threads):
```python
# ✅ RIGHT - All 4 at same time
Thread 1: listen_to_machine("CNC_01")
Thread 2: listen_to_machine("CNC_02")
Thread 3: listen_to_machine("PUMP_03")
Thread 4: listen_to_machine("CONVEYOR")
# Total: 10 seconds to get data from all 4!
```

### Thread Visualization

```
Main Thread
    │
    ├─→ [Thread 1] ━━━━━━━━━━━━━━━━━━━━━━━━→ CNC_01
    │               listens forever
    │
    ├─→ [Thread 2] ━━━━━━━━━━━━━━━━━━━━━━━━→ CNC_02
    │               listens forever
    │
    ├─→ [Thread 3] ━━━━━━━━━━━━━━━━━━━━━━━━→ PUMP_03
    │               listens forever
    │
    └─→ [Thread 4] ━━━━━━━━━━━━━━━━━━━━━━━━→ CONVEYOR_04
                    listens forever
```

All running **simultaneously**!

---

## How to Use: Step by Step

### Step 1: Import the Client
```python
from data.api_stream_client import StreamAPIClient

client = StreamAPIClient(base_url="http://localhost:3000")
```

### Step 2: Define a Callback
```python
def on_machine_data(machine_id, data):
    """Called when data arrives from ANY machine"""
    print(f"{machine_id}: {data['temperature_C']}°C")
```

### Step 3: Start Listening
```python
machines = ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"]
threads = client.listen_all_machines(machines, on_machine_data)
```

### Step 4: Keep Running
```python
import time
while True:
    time.sleep(1)
    # Threads keep listening in background
```

---

## With AI Agent (Full Example)

```python
from data.api_stream_client import StreamAPIClient
from agent.decision_agent import DecisionAgent

# Setup
client = StreamAPIClient("http://localhost:3000")
agent = DecisionAgent(model)

# Callback processes with AI
def on_data(machine_id, data):
    # 🤖 AI Decision
    result = agent.analyze(data, machine_id)
    
    if result['decision'] == 'CRITICAL':
        # Send alert back to API
        client.send_alert(
            machine_id=machine_id,
            alert_type=result['decision'],
            message=result['recommendation'],
            data=data
        )

# Listen to all
client.listen_all_machines(
    ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"],
    on_data
)
```

---

## Flow of Data

```
Physical Machine
    │
    ├─ Sensors measure (Temp, Vibration, RPM, Current)
    │
    └─→ API Server (localhost:3000)
           │
           ├─ /stream/CNC_01 (SSE)
           │  ├─ data: {"temperature_C": 75.5, ...}
           │  ├─ data: {"temperature_C": 75.6, ...}
           │  └─ data: {"temperature_C": 75.7, ...}
           │
           ├─ /stream/CNC_02 (SSE)
           │  └─ (similar stream)
           │
           ├─ /stream/PUMP_03 (SSE)
           │  └─ (similar stream)
           │
           └─ /stream/CONVEYOR_04 (SSE)
              └─ (similar stream)
                  │
                  └─→ Python Client (our code)
                       │
                       ├─→ Thread 1 (listens CNC_01)
                       ├─→ Thread 2 (listens CNC_02)
                       ├─→ Thread 3 (listens PUMP_03)
                       └─→ Thread 4 (listens CONVEYOR_04)
                            │
                            └─→ AI Agent (processes)
                                 │
                                 ├─ ML Analysis
                                 ├─ Rule Checking
                                 ├─ Decision Making
                                 └─ Action Execution
                                      │
                                      └─→ API Server /alert (POST)
```

---

## Real-Time Processing Flow

```
TIME →

t=0s   [T1: CNC_01 arrives] →→→ AI Agent → Decision → Result 1
       [T2: CNC_02 arrives] →→→ AI Agent → Decision → Result 2
       [T3: PUMP_03 arrives] →→→ AI Agent → Decision → Result 3
       [T4: CONVEYOR_04 arrives] →→→ AI Agent → Decision → Result 4

t=1s   [T1: CNC_01 arrives] →→→ AI Agent → Decision → Result 5
       [T2: CNC_02 arrives] →→→ AI Agent → Decision → Result 6
       [T3: PUMP_03 arrives] →→→ AI Agent → Decision → Result 7
       [T4: CONVEYOR_04 arrives] →→→ AI Agent → Decision → Result 8

t=2s   ...continuing in parallel...

All 4 machines processed simultaneously!
```

---

## Key Methods in StreamAPIClient

### listen_all_machines() - The Main Method
```python
def listen_all_machines(
    machine_ids: List[str],      # ["CNC_01", "CNC_02", ...]
    callback: Callable,          # function(machine_id, data)
    error_callback: Callable     # function(machine_id, error)
) -> Dict[str, threading.Thread]:
    """
    Start parallel listeners for all machines
    Returns dictionary of {machine_id: thread}
    """
```

### listen_to_machine() - Single Machine
```python
def listen_to_machine(
    machine_id: str,             # "CNC_01"
    callback: Callable[[Dict], None],  # function(data)
    error_callback: Callable = None
):
    """
    Listen to ONE machine (runs in current thread)
    Use in a Thread if you want parallelism
    """
```

### send_alert() - Send Alert Back
```python
def send_alert(
    machine_id: str,             # "CNC_01"
    alert_type: str,             # "CRITICAL"
    message: str,                # "High vibration detected"
    data: Dict                   # The sensor reading
) -> bool:
```

### stop_listening() - Graceful Shutdown
```python
def stop_listening():
    """Stop all listening threads"""
```

---

## Working Code Example

### Example 1: Simple Listener
```python
from data.api_stream_client import StreamAPIClient

client = StreamAPIClient("http://localhost:3000")

def on_data(machine_id, data):
    print(f"{machine_id}: {data['temperature_C']}°C")

# Listen to all 4 machines
client.listen_all_machines(
    ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"],
    on_data
)

# Keep running
import time
while True:
    time.sleep(1)
```

### Example 2: With AI Agent
```python
from data.api_stream_client import StreamAPIClient
from agent.decision_agent import DecisionAgent

client = StreamAPIClient("http://localhost:3000")
agent = DecisionAgent(model)

def on_data(machine_id, data):
    # Get AI decision
    result = agent.analyze(data, machine_id)
    
    # Send alert if critical
    if result['decision'] == 'CRITICAL':
        client.send_alert(
            machine_id=machine_id,
            alert_type=result['decision'],
            message=result['recommendation'],
            data=data
        )

client.listen_all_machines(
    ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"],
    on_data
)

while True:
    time.sleep(1)
```

### Example 3: With Error Handling
```python
def on_error(machine_id, error_msg):
    print(f"Error in {machine_id}: {error_msg}")

client.listen_all_machines(
    machines,
    callback=on_data,
    error_callback=on_error
)
```

---

## Important Details

### Daemon Threads
Threads are set to `daemon=True`:
- Main program can exit anytime
- Threads don't block shutdown
- Clean shutdown is automatic

### No Polling
Completely event-driven:
- Data arrives → callback is called
- No wasted CPU on polling
- Truly real-time

### Parallel Processing
All 4 machines run independently:
- Network calls are non-blocking (streaming)
- AI processing happens in parallel
- No waiting for one machine before another

### Error Resilience
Each thread can fail independently:
- One machine down doesn't stop others
- Errors logged but don't crash program
- Optional error_callback for custom handling

---

## Testing

### Test 1: Check Connection
```bash
curl http://localhost:3000/health
# Should return 200 OK
```

### Test 2: Test One Stream
```bash
curl http://localhost:3000/stream/CNC_01
# Should show data: {...}
```

### Test 3: Run Example
```bash
python examples/stream_example.py
# Choose option 1 (Test all streams)
```

### Test 4: Full System
```bash
python examples/stream_example.py
# Choose option 0 (Real-time detector)
```

---

## Integration into Dashboard

In `dashboard/app.py`:

### Instead of pulling data:
```python
# ❌ Old way
def advance_stream():
    snapshot = get_live_snapshot(MACHINE_IDS)
    for reading in snapshot:
        process(reading)
```

### Use streaming:
```python
# ✅ New way
from data.api_stream_client import StreamAPIClient

client = StreamAPIClient("http://localhost:3000")

def on_machine_data(machine_id, data):
    # Process data in real-time
    agent.analyze(data, machine_id)

# Start listening (background threads)
client.listen_all_machines(MACHINE_IDS, on_machine_data)
```

---

## Summary

| Aspect | Before (Polling) | Now (Streaming) |
|--------|------------------|-----------------|
| Method | REST GET (repeated) | SSE (persistent) |
| All machines | Sequential | Parallel (threads) |
| Response time | Delay (1-5s) | Instant (< 100ms) |
| CPU usage | High (constant polling) | Low (event-driven) |
| Scalability | Poor (n streams = n requests/sec) | Excellent (truly streaming) |

**This is the RIGHT way to build real-time monitoring!** 🔥

---

## Next Steps

1. ✅ Test API: `curl http://localhost:3000/stream/CNC_01`
2. ✅ Run example: `python examples/stream_example.py`
3. ✅ Integrate into dashboard using `listen_all_machines()`
4. ✅ Deploy and monitor all 4 machines in real-time

---

**Ready?** Run the stream example now! 🚀
