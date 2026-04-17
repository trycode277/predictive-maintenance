# 🔧 How to Integrate API into Dashboard

## Quick Steps (5 minutes)

### Step 1: Test if API is Running
```bash
# PowerShell or CMD
curl http://localhost:3000/stream/CNC_01

# Should return JSON like:
# {"machine_id":"CNC_01","temperature_C":75.5,...}
```

✅ If you see JSON data, API is working!
❌ If error, start your API server first

---

### Step 2: Modify Dashboard

**File**: `c:\Users\dayan\predictive-maintenance\dashboard\app.py`

**Find this function** (around line 2031):
```python
def advance_stream():
    snapshot = get_live_snapshot(MACHINE_IDS)
    for raw_reading in snapshot:
        machine_id = raw_reading["machine_id"]
        reading = preprocess(raw_reading)
        save_data(machine_id, reading)

        buffer = st.session_state.machine_buffers[machine_id]
        buffer.append(reading)
        if len(buffer) > BUFFER_SIZE:
            buffer.pop(0)

        reading_timestamp = parse_timestamp(reading.get("timestamp"))
        if reading_timestamp is not None:
            st.session_state.last_seen[machine_id] = reading_timestamp
```

**Replace with this** (API + Fallback):
```python
from data.api_client import APIClient

# Initialize API client (once at startup)
API_CLIENT = APIClient(base_url="http://localhost:3000")

def advance_stream():
    """Get live data from API with fallback to local"""
    snapshot = []
    
    # Try to get data from API
    for machine_id in MACHINE_IDS:
        data = API_CLIENT.get_live_stream(machine_id)
        
        # Fallback to local if API fails
        if not data:
            local_snapshot = get_live_snapshot([machine_id])
            if local_snapshot:
                data = local_snapshot[0]
        
        if data:
            snapshot.append(data)
    
    # Process data (same as before)
    for raw_reading in snapshot:
        machine_id = raw_reading["machine_id"]
        reading = preprocess(raw_reading)
        save_data(machine_id, reading)

        buffer = st.session_state.machine_buffers[machine_id]
        buffer.append(reading)
        if len(buffer) > BUFFER_SIZE:
            buffer.pop(0)

        reading_timestamp = parse_timestamp(reading.get("timestamp"))
        if reading_timestamp is not None:
            st.session_state.last_seen[machine_id] = reading_timestamp
```

---

## Method 1: Pure API (No Fallback)

### When to Use
- API is always reliable
- You only have API source
- Production environment

### Code

**Add at top of file** (after imports):
```python
from data.api_client import APIClient

API_CLIENT = APIClient(base_url="http://localhost:3000")
```

**Replace advance_stream() with**:
```python
def advance_stream():
    """Get live data directly from API"""
    snapshot = []
    
    for machine_id in MACHINE_IDS:
        data = API_CLIENT.get_live_stream(machine_id)
        if data:
            snapshot.append(data)
    
    for raw_reading in snapshot:
        machine_id = raw_reading["machine_id"]
        reading = preprocess(raw_reading)
        save_data(machine_id, reading)

        buffer = st.session_state.machine_buffers[machine_id]
        buffer.append(reading)
        if len(buffer) > BUFFER_SIZE:
            buffer.pop(0)

        reading_timestamp = parse_timestamp(reading.get("timestamp"))
        if reading_timestamp is not None:
            st.session_state.last_seen[machine_id] = reading_timestamp
```

---

## Method 2: Hybrid (Recommended)

### When to Use
- API might go down sometimes
- Want to test with local data
- Best reliability

### Code

**Add at top of file**:
```python
from data.api_client import APIClient

API_CLIENT = APIClient(base_url="http://localhost:3000")
API_HEALTHY = False  # Track API status

def check_api_health():
    """Check if API is available"""
    global API_HEALTHY
    API_HEALTHY = API_CLIENT.health_check()
    return API_HEALTHY
```

**In live_monitoring_dashboard() function** (add this):
```python
def live_monitoring_dashboard():
    baselines = build_baselines("data/sample_data.csv")
    model = load_model("data/sample_data.csv")
    agent = load_agent("data/sample_data.csv")
    
    # NEW: Check API health
    check_api_health()
    
    render_workspace_header(...)
    # ... rest of function
```

**Replace advance_stream() with**:
```python
def advance_stream():
    """Get live data from API if available, fallback to local"""
    snapshot = []
    
    if API_HEALTHY:
        # Try to get from API
        for machine_id in MACHINE_IDS:
            data = API_CLIENT.get_live_stream(machine_id)
            if data:
                snapshot.append(data)
    
    # If no API data, use local simulation
    if not snapshot:
        snapshot = get_live_snapshot(MACHINE_IDS)
    
    # Process data (same as before)
    for raw_reading in snapshot:
        machine_id = raw_reading["machine_id"]
        reading = preprocess(raw_reading)
        save_data(machine_id, reading)

        buffer = st.session_state.machine_buffers[machine_id]
        buffer.append(reading)
        if len(buffer) > BUFFER_SIZE:
            buffer.pop(0)

        reading_timestamp = parse_timestamp(reading.get("timestamp"))
        if reading_timestamp is not None:
            st.session_state.last_seen[machine_id] = reading_timestamp
```

**Optional: Show API status in sidebar**:
```python
def live_monitoring_dashboard():
    # ... existing code ...
    
    st.sidebar.header("Monitoring control")
    
    # NEW: Show API status
    if API_HEALTHY:
        st.sidebar.success("✅ API Connected")
    else:
        st.sidebar.warning("⚠️ Using Local Data")
    
    # ... rest of function ...
```

---

## Method 3: API for Historical, Local for Live

### When to Use
- Historical data from API (7 days)
- Live data from local (faster)
- Best performance

### Code

**Add at top**:
```python
from data.api_client import APIClient

API_CLIENT = APIClient(base_url="http://localhost:3000")
```

**Keep advance_stream() as is** (no changes)
```python
def advance_stream():
    # No changes - still uses get_live_snapshot()
    snapshot = get_live_snapshot(MACHINE_IDS)
    # ... same code ...
```

**Replace load_historical_frame()**:
```python
@st.cache_data(show_spinner=False)
def load_historical_frame(path):
    """Load historical data from API if available"""
    try:
        # Try to get from API
        history_data = API_CLIENT.get_historical_data("CNC_01", days=7)
        if history_data:
            historical = pd.DataFrame(history_data)
        else:
            # Fallback to CSV
            historical = pd.DataFrame(load_csv_data(path))
    except:
        # Fallback to CSV
        historical = pd.DataFrame(load_csv_data(path))
    
    # Rest of function stays the same
    rename_map = {
        "temp_1": "temperature_C",
        "vibration_1": "vibration_mm_s",
        "rpm_1": "rpm",
        "current_1": "current_A",
    }
    historical = historical.rename(columns=rename_map)

    if "machine_id" not in historical.columns:
        historical["machine_id"] = "CNC_01"

    for column in FEATURE_COLUMNS:
        historical[column] = pd.to_numeric(historical[column], errors="coerce")

    return historical
```

---

## Testing Your Integration

### Step 1: Check Syntax
```bash
cd c:\Users\dayan\predictive-maintenance
python -m py_compile dashboard/app.py
```

✅ No errors = Good!
❌ Errors = Fix and try again

### Step 2: Start Dashboard
```bash
streamlit run dashboard/app.py
```

### Step 3: Verify It Works

**With API Running:**
- Check sidebar shows "✅ API Connected" (if you added status)
- Check machines have data
- Verify agent decisions are working

**With API Down:**
- Should fallback to local data (Hybrid method)
- Still see machines running
- Still see agent decisions

---

## Integration Checklist

- [ ] API server is running on `http://localhost:3000`
- [ ] Tested API with curl or browser
- [ ] Added `from data.api_client import APIClient`
- [ ] Created `API_CLIENT` instance
- [ ] Modified `advance_stream()` function
- [ ] Tested syntax: `python -m py_compile dashboard/app.py`
- [ ] Started dashboard: `streamlit run dashboard/app.py`
- [ ] Verified data is coming in
- [ ] Checked agent decisions are working
- [ ] Monitor for errors in console

---

## Troubleshooting

### "Cannot connect to API"
```python
# Check if API is running
from data.api_client import APIClient
client = APIClient("http://localhost:3000")
print(client.health_check())  # Should be True
```

**Fix:**
1. Make sure API server is running
2. Check it's on port 3000
3. Try: `curl http://localhost:3000/health`

### "Getting None values"
```python
# Check API response
data = API_CLIENT.get_live_stream("CNC_01")
print(data)  # Should print dictionary, not None
```

**Fix:**
1. Verify machine ID is correct
2. Check API is returning valid JSON
3. Use hybrid method with fallback

### "Dashboard is slow"
```python
# Increase timeout
API_CLIENT = APIClient(base_url="http://localhost:3000", timeout=10)
```

**Fix:**
1. Increase timeout value
2. Use hybrid method (falls back to local if slow)
3. Check if API server is overloaded

---

## Quick Copy-Paste Solutions

### Complete advance_stream() - Hybrid Method
```python
def advance_stream():
    """Get live data from API with fallback to local"""
    snapshot = []
    
    # Get from API
    for machine_id in MACHINE_IDS:
        data = API_CLIENT.get_live_stream(machine_id)
        if data:
            snapshot.append(data)
    
    # Fallback to local if no API data
    if not snapshot:
        snapshot = get_live_snapshot(MACHINE_IDS)
    
    # Process
    for raw_reading in snapshot:
        machine_id = raw_reading["machine_id"]
        reading = preprocess(raw_reading)
        save_data(machine_id, reading)
        buffer = st.session_state.machine_buffers[machine_id]
        buffer.append(reading)
        if len(buffer) > BUFFER_SIZE:
            buffer.pop(0)
        reading_timestamp = parse_timestamp(reading.get("timestamp"))
        if reading_timestamp is not None:
            st.session_state.last_seen[machine_id] = reading_timestamp
```

### Import and Initialize
```python
# Add after existing imports
from data.api_client import APIClient

# Add after imports
API_CLIENT = APIClient(base_url="http://localhost:3000")
```

---

## Next Steps

1. ✅ Choose integration method (Pure/Hybrid/Mixed)
2. ✅ Make the code changes
3. ✅ Test with `python -m py_compile`
4. ✅ Start dashboard: `streamlit run dashboard/app.py`
5. ✅ Verify data is flowing
6. ✅ Monitor for errors

---

**Ready to integrate?** Follow the steps above and you'll be connected to real data in minutes! 🚀
