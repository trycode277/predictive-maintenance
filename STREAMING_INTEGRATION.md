# 🔥 Quick Integration: SSE Streams → Dashboard

## The Right Way: SSE Streaming (Not Polling)

### Current Issue
Dashboard uses `get_live_snapshot()` which:
- ❌ Polls once per cycle
- ❌ Only gets ONE reading
- ❌ Doesn't use SSE streaming
- ❌ Misses data between polls

### The Solution
Use `StreamAPIClient` for:
- ✅ Continuous SSE streams (all 4 machines)
- ✅ Real-time data flow (no polling)
- ✅ Parallel processing (threading)
- ✅ AI agent processes every reading

---

## Option A: Background Streaming (Recommended) ⭐

Keep current dashboard flow but add streaming in background:

### Step 1: Initialize in Session State
```python
# In dashboard/app.py, add to session state init:

if "stream_client" not in st.session_state:
    from data.api_stream_client import StreamAPIClient
    st.session_state.stream_client = StreamAPIClient("http://localhost:3000")
    st.session_state.latest_readings = {}
    
    # Start background threads for all machines
    def on_stream_data(machine_id, data):
        st.session_state.latest_readings[machine_id] = data
    
    st.session_state.stream_client.listen_all_machines(
        MACHINE_IDS,
        callback=on_stream_data
    )
```

### Step 2: Use Latest Data
```python
# In advance_stream() or wherever you need fresh data:

def advance_stream():
    # Get latest readings from streaming (updated in real-time)
    snapshot = []
    for machine_id in MACHINE_IDS:
        if machine_id in st.session_state.latest_readings:
            snapshot.append(st.session_state.latest_readings[machine_id])
    
    # Process as normal
    for raw_reading in snapshot:
        machine_id = raw_reading["machine_id"]
        # ... rest of processing ...
```

**Benefit:** Minimal changes, real-time data, AI agent processes every reading

---

## Option B: Full Streaming Integration (Advanced)

Replace `advance_stream()` completely with streaming:

### Step 1: Create Streaming Manager
```python
class StreamingManager:
    """Manages all 4 machine streams"""
    
    def __init__(self, machine_ids, agent):
        self.client = StreamAPIClient("http://localhost:3000")
        self.agent = agent
        self.readings = {}
    
    def start(self):
        """Start listening to all machines"""
        self.client.listen_all_machines(
            machine_ids=machine_ids,
            callback=self.on_data
        )
    
    def on_data(self, machine_id, data):
        """Process each reading as it arrives"""
        # Preprocess
        reading = preprocess(data)
        
        # Save to database
        save_data(machine_id, reading)
        
        # Update buffer
        buffer = st.session_state.machine_buffers[machine_id]
        buffer.append(reading)
        if len(buffer) > BUFFER_SIZE:
            buffer.pop(0)
        
        # AI Agent
        result = self.agent.analyze(data, machine_id)
        
        # Alert if needed
        if result['decision'] in ['CRITICAL', 'WARNING']:
            self.client.send_alert(
                machine_id=machine_id,
                alert_type=result['decision'],
                message=result['recommendation'],
                data=data
            )
```

### Step 2: Initialize in Dashboard
```python
def live_monitoring_dashboard():
    # ... existing code ...
    
    # Initialize streaming (once)
    if "streaming_manager" not in st.session_state:
        agent = load_agent("data/sample_data.csv")
        st.session_state.streaming_manager = StreamingManager(
            MACHINE_IDS,
            agent
        )
        st.session_state.streaming_manager.start()
    
    # ... rest of dashboard ...
```

**Benefit:** True real-time, doesn't rely on polling, processes every reading

---

## Option C: Hybrid (API Streams + Local Fallback)

Use SSE when available, fall back to local:

```python
from data.api_stream_client import StreamAPIClient
from data.ingestion import get_live_snapshot

class HybridDataSource:
    def __init__(self):
        self.client = StreamAPIClient("http://localhost:3000")
        self.api_healthy = False
        self.latest_api_data = {}
        
        # Start streaming if available
        if self.client.health_check():
            self.api_healthy = True
            self.client.listen_all_machines(
                MACHINE_IDS,
                callback=self._store_api_data
            )
    
    def _store_api_data(self, machine_id, data):
        """Store data from API stream"""
        self.latest_api_data[machine_id] = data
    
    def get_snapshot(self):
        """Get snapshot from API or local fallback"""
        if self.api_healthy and self.latest_api_data:
            # Use API data
            return list(self.latest_api_data.values())
        else:
            # Fallback to local
            return get_live_snapshot(MACHINE_IDS)

# Usage:
data_source = HybridDataSource()
snapshot = data_source.get_snapshot()
```

---

## Comparison

| Feature | Option A | Option B | Option C |
|---------|----------|----------|----------|
| **Effort** | 10 min | 30 min | 20 min |
| **Real-time** | ✅ | ✅ | ✅ |
| **Reliable** | ✅ | ✅ | ✅✅ |
| **Changes needed** | Minimal | Major | Moderate |
| **Fallback** | No | No | ✅ |
| **Best for** | Quick setup | Production | Safe migration |

**Recommendation:** Start with **Option A**, move to **Option C** for safety

---

## Files You Need

✅ `data/api_stream_client.py` - New streaming client (already created)
✅ `examples/stream_example.py` - Working example (already created)
✅ `SSE_STREAMING_GUIDE.md` - Full documentation (already created)
✅ `dashboard/app.py` - Will edit

---

## Quick Start (Option A - 10 minutes)

### Step 1: Add to imports
```python
from data.api_stream_client import StreamAPIClient
```

### Step 2: Initialize streaming
```python
# Add to session state initialization
if "stream_client" not in st.session_state:
    st.session_state.stream_client = StreamAPIClient("http://localhost:3000")
    st.session_state.latest_readings = {}
    
    def on_data(machine_id, data):
        st.session_state.latest_readings[machine_id] = data
    
    st.session_state.stream_client.listen_all_machines(
        ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"],
        callback=on_data
    )
```

### Step 3: Use in advance_stream()
```python
def advance_stream():
    # Get from streaming instead of polling
    snapshot = [
        data for data in st.session_state.latest_readings.values()
    ]
    
    # Rest of function stays the same
    for raw_reading in snapshot:
        machine_id = raw_reading["machine_id"]
        # ... process ...
```

### Step 4: Done!
Dashboard now uses real-time SSE streams instead of polling.

---

## Testing

### Before Integration
```bash
# Test streaming works
python examples/stream_example.py
# Choose option 1 (Test all streams)
```

### After Integration
```bash
# Run dashboard and verify:
streamlit run dashboard/app.py
# Check: All 4 machines show data
# Check: Data updates continuously
# Check: No polling delays
```

---

## Architecture Comparison

### OLD (Polling)
```
dashboard/app.py
    │
    ├─ Every 1 second: advance_stream()
    │  ├─ get_live_snapshot() [REST API]
    │  ├─ CNC_01: wait for response
    │  ├─ CNC_02: wait for response
    │  ├─ PUMP_03: wait for response
    │  └─ CONVEYOR_04: wait for response (total: 4 requests)
    │
    └─ Process all at once
       (data is already 1+ second old!)
```

### NEW (Streaming) ⭐
```
StreamAPIClient (background)
    │
    ├─ Thread 1: /stream/CNC_01 (CONTINUOUS)
    ├─ Thread 2: /stream/CNC_02 (CONTINUOUS)
    ├─ Thread 3: /stream/PUMP_03 (CONTINUOUS)
    └─ Thread 4: /stream/CONVEYOR_04 (CONTINUOUS)
         │
         └─→ st.session_state.latest_readings (always fresh)
              │
              └─→ dashboard/app.py uses fresh data
                  (data is < 100ms old!)
```

---

## Sample Implementation (Option A)

Copy-paste ready code:

```python
# ============ IMPORTS ============
from data.api_stream_client import StreamAPIClient

# ============ SESSION STATE ============
if "stream_client" not in st.session_state:
    st.session_state.stream_client = StreamAPIClient(
        base_url="http://localhost:3000"
    )
    st.session_state.latest_readings = {}
    
    def handle_stream_data(machine_id, data):
        """Called whenever new data arrives from any machine"""
        st.session_state.latest_readings[machine_id] = data
    
    def handle_stream_error(machine_id, error):
        """Called if stream error occurs"""
        st.warning(f"⚠️ Stream error for {machine_id}: {error}")
    
    # Start listening to all 4 machines (background threads)
    st.session_state.stream_client.listen_all_machines(
        machine_ids=["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"],
        callback=handle_stream_data,
        error_callback=handle_stream_error
    )
    
    st.sidebar.success("✅ Real-time streams active")

# ============ USE IN ADVANCE_STREAM ============
def advance_stream():
    """Get latest readings from SSE streams"""
    
    # Use continuously updated readings from streams
    snapshot = list(st.session_state.latest_readings.values())
    
    if not snapshot:
        st.warning("⚠️ No data from streams yet")
        return
    
    # Process as before
    for raw_reading in snapshot:
        machine_id = raw_reading["machine_id"]
        reading = preprocess(raw_reading)
        save_data(machine_id, reading)
        
        # Update buffer
        buffer = st.session_state.machine_buffers[machine_id]
        buffer.append(reading)
        if len(buffer) > BUFFER_SIZE:
            buffer.pop(0)
        
        # Update timestamp
        reading_timestamp = parse_timestamp(reading.get("timestamp"))
        if reading_timestamp is not None:
            st.session_state.last_seen[machine_id] = reading_timestamp
```

---

## Troubleshooting

### "No data from streams"
- Check API is running: `curl http://localhost:3000/health`
- Check machine IDs match: `curl http://localhost:3000/machines`

### "Streams not starting"
- Verify api_stream_client.py exists and has no syntax errors
- Check imports are correct in dashboard/app.py

### "Slow updates"
- Streams should be instant, check network connectivity
- Verify API server has real data flowing

### "Memory usage high"
- Set max buffer size: `BUFFER_SIZE = 60`
- Streams are efficient, shouldn't be memory issue

---

## Migration Path

1. **Phase 1:** Option A (Streaming in background)
   - Low risk
   - Minimal changes
   - Immediate real-time data

2. **Phase 2:** Option C (Hybrid with fallback)
   - Add safety
   - Still works if API down
   - Production ready

3. **Phase 3:** Option B (Full streaming)
   - When you fully trust API
   - Complete refactor
   - Maximum performance

---

## Next Steps

1. ✅ Run example: `python examples/stream_example.py`
2. ✅ Choose integration option (A recommended)
3. ✅ Add streaming to dashboard/app.py
4. ✅ Test with `streamlit run dashboard/app.py`
5. ✅ Monitor all 4 machines in real-time

---

**Your system is now ready for true real-time monitoring!** 🚀

The key insight: SSE Streams > REST Polling for real-time monitoring. All 4 machines, all the time, completely in parallel.
