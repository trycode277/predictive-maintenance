# 🌐 API Integration Guide

## Overview

Your system can now connect to **external APIs** to get real-time data instead of using simulated data.

```
External API Server (localhost:3000)
         ↓
    API Client
         ↓
   Dashboard
         ↓
   Real Machines!
```

---

## APIs Available

### 1. **Live Data Stream**
```
GET http://localhost:3000/stream/{machine_id}
```

**Returns single sensor reading**:
```json
{
    "machine_id": "CNC_01",
    "timestamp": "2024-04-17T12:34:56Z",
    "temperature_C": 75.5,
    "vibration_mm_s": 2.1,
    "rpm": 1500,
    "current_A": 15.8,
    "status": "running"
}
```

### 2. **Historical Data**
```
GET http://localhost:3000/history/{machine_id}?days=7
```

**Returns last 7 days of data**:
```json
[
    {
        "machine_id": "CNC_01",
        "timestamp": "2024-04-10T00:00:00Z",
        "temperature_C": 72.5,
        ...
    },
    ...
]
```

### 3. **Available Machines**
```
GET http://localhost:3000/machines
```

**Returns list of machines**:
```json
["CNC_01", "CNC_02", "CNC_03", "CNC_04"]
```

### 4. **Health Check**
```
GET http://localhost:3000/health
```

---

## Testing the APIs

### Option 1: Command Line (PowerShell)

```powershell
# Test live stream
curl http://localhost:3000/stream/CNC_01

# Test historical data
curl "http://localhost:3000/history/CNC_01?days=7"

# Test machines list
curl http://localhost:3000/machines

# Test health
curl http://localhost:3000/health
```

### Option 2: Python

```python
# Install requests if needed
pip install requests

# Test in Python
import requests

base_url = "http://localhost:3000"

# Live stream
response = requests.get(f"{base_url}/stream/CNC_01")
print(response.json())

# Historical data
response = requests.get(f"{base_url}/history/CNC_01", params={"days": 7})
print(len(response.json()), "records fetched")

# Machines list
response = requests.get(f"{base_url}/machines")
print(response.json())
```

### Option 3: Browser
Simply open in browser (returns JSON):
```
http://localhost:3000/stream/CNC_01
http://localhost:3000/history/CNC_01?days=7
http://localhost:3000/machines
http://localhost:3000/health
```

---

## Using the API Client

### Basic Usage

```python
from data.api_client import APIClient

# Create client
client = APIClient(base_url="http://localhost:3000")

# Get live data for one machine
live_data = client.get_live_stream("CNC_01")
print(live_data)
# Output:
# {
#     "machine_id": "CNC_01",
#     "timestamp": "2024-04-17T12:34:56Z",
#     "temperature_C": 75.5,
#     ...
# }

# Get historical data (7 days)
history = client.get_historical_data("CNC_01", days=7)
print(f"Got {len(history)} historical records")

# Get all machines
machines = client.get_all_machines()
print(machines)  # ["CNC_01", "CNC_02", ...]

# Check if server is alive
if client.health_check():
    print("✅ API Server is running!")
else:
    print("❌ API Server is down")
```

### Context Manager Usage

```python
from data.api_client import APIClient

# Automatically closes connection
with APIClient(base_url="http://localhost:3000") as client:
    data = client.get_live_stream("CNC_01")
    print(data)
```

---

## Integration with Dashboard

### Option A: Replace Local Data with API (Recommended)

**File**: `dashboard/app.py`

**Old way** (local simulation):
```python
def advance_stream():
    snapshot = get_live_snapshot(MACHINE_IDS)  # ← Local data
    for raw_reading in snapshot:
        # ...
```

**New way** (external API):
```python
from data.api_client import APIClient

def advance_stream():
    client = APIClient(base_url="http://localhost:3000")
    snapshot = []
    
    for machine_id in MACHINE_IDS:
        data = client.get_live_stream(machine_id)
        if data:
            snapshot.append(data)
    
    for raw_reading in snapshot:
        # ... rest stays the same
```

### Option B: Hybrid Mode (API + Fallback)

Use API if available, fallback to local simulation:

```python
from data.api_client import APIClient

API_CLIENT = APIClient(base_url="http://localhost:3000")

def advance_stream():
    snapshot = []
    
    for machine_id in MACHINE_IDS:
        # Try API first
        data = API_CLIENT.get_live_stream(machine_id)
        
        # Fallback to local if API fails
        if not data:
            snapshot_local = get_live_snapshot([machine_id])
            if snapshot_local:
                data = snapshot_local[0]
        
        if data:
            snapshot.append(data)
    
    for raw_reading in snapshot:
        # ... process data
```

### Option C: Use API for Historical, Local for Live

```python
def load_historical_frame(path):
    """Load historical data from API instead of CSV"""
    client = APIClient(base_url="http://localhost:3000")
    
    # Get data from API
    raw_data = client.get_historical_data("CNC_01", days=7)
    
    if raw_data:
        historical = pd.DataFrame(raw_data)
    else:
        # Fallback to CSV
        historical = pd.DataFrame(load_csv_data(path))
    
    return historical
```

---

## Complete Integration Example

Here's a complete function to integrate APIs into your dashboard:

```python
from data.api_client import APIClient
import pandas as pd

class DataManager:
    """Manages data from APIs or local sources"""
    
    def __init__(self, api_url="http://localhost:3000", use_api=True):
        self.api_url = api_url
        self.use_api = use_api
        self.client = APIClient(base_url=api_url) if use_api else None
        self.api_healthy = self._check_api_health()
    
    def _check_api_health(self):
        """Check if API is available"""
        if not self.use_api:
            return False
        try:
            return self.client.health_check()
        except:
            return False
    
    def get_live_data(self, machine_ids):
        """Get live data from API or local"""
        if self.api_healthy:
            return self._get_from_api(machine_ids)
        else:
            return self._get_from_local(machine_ids)
    
    def _get_from_api(self, machine_ids):
        """Fetch from external API"""
        snapshot = []
        for machine_id in machine_ids:
            data = self.client.get_live_stream(machine_id)
            if data:
                snapshot.append(data)
        return snapshot
    
    def _get_from_local(self, machine_ids):
        """Fallback to local simulation"""
        return get_live_snapshot(machine_ids)
    
    def get_historical_data(self, machine_id, days=7):
        """Get historical data from API or CSV"""
        if self.api_healthy:
            data = self.client.get_historical_data(machine_id, days=days)
            if data:
                return pd.DataFrame(data)
        
        # Fallback to CSV
        return pd.DataFrame(load_csv_data("data/sample_data.csv"))

# Usage in dashboard
data_manager = DataManager(api_url="http://localhost:3000", use_api=True)

def advance_stream():
    snapshot = data_manager.get_live_data(MACHINE_IDS)
    for raw_reading in snapshot:
        # ... process as before
```

---

## How the Connection Works

```
┌─────────────────────────────────────────────────────┐
│                Your Dashboard                        │
│              (Streamlit App)                         │
└────────────────────┬────────────────────────────────┘
                     │
                     │ (1) Request live data
                     ↓
        ┌────────────────────────┐
        │   APIClient            │
        │ (data/api_client.py)   │
        └────────────┬───────────┘
                     │
                     │ (2) HTTP GET request
                     ↓
        ┌────────────────────────┐
        │   External API Server  │
        │  http://localhost:3000 │
        │                        │
        │  GET /stream/CNC_01    │
        │  GET /history/CNC_01   │
        │  GET /machines         │
        │  GET /health           │
        └────────────┬───────────┘
                     │
                     │ (3) JSON response
                     ↓
        ┌────────────────────────┐
        │   Normalize Data       │
        │                        │
        │   Convert to standard  │
        │   format               │
        └────────────┬───────────┘
                     │
                     │ (4) Return dictionary
                     ↓
        ┌────────────────────────┐
        │   Process in Dashboard │
        │                        │
        │   - Preprocess         │
        │   - Buffer             │
        │   - Analyze            │
        │   - Display            │
        └────────────────────────┘
```

---

## Error Handling

The API client handles these errors gracefully:

```
❌ Connection Error     → Logs error, returns None, fallback available
⏱️  Timeout            → Logs error, returns None, fallback available
🔴 HTTP Error          → Logs error, returns None, fallback available
📝 Invalid JSON         → Logs error, returns None, fallback available
⚠️  Unexpected Error    → Logs error, returns None, fallback available
```

---

## Configuration

### Change API URL

```python
# Production
client = APIClient(base_url="http://api.example.com")

# Development
client = APIClient(base_url="http://localhost:3000")

# Different port
client = APIClient(base_url="http://localhost:5000")
```

### Change Timeout

```python
# 10 second timeout
client = APIClient(base_url="http://localhost:3000", timeout=10)
```

---

## Quick Start

### Step 1: Start Your API Server
```bash
# Run your API server on port 3000
# Make sure it's accessible at http://localhost:3000
```

### Step 2: Test the Connection
```python
from data.api_client import APIClient

client = APIClient(base_url="http://localhost:3000")

# Test
if client.health_check():
    print("✅ Connected!")
    print(client.get_live_stream("CNC_01"))
else:
    print("❌ Cannot connect to API")
```

### Step 3: Use in Dashboard

**Option A - Quick integration** (replace one function):
```python
# In dashboard/app.py, replace advance_stream():
from data.api_client import APIClient

client = APIClient(base_url="http://localhost:3000")

def advance_stream():
    snapshot = []
    for machine_id in MACHINE_IDS:
        data = client.get_live_stream(machine_id)
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

**Option B - Full integration** (use DataManager class above)

---

## Troubleshooting

### "Cannot reach API"
```
✓ Check API server is running on http://localhost:3000
✓ Check no firewall blocking the port
✓ Try: curl http://localhost:3000/health
✓ Check logs for details
```

### "Invalid JSON response"
```
✓ Verify API returns valid JSON
✓ Check response with curl first
✓ Verify data format matches expected structure
```

### "Timeout"
```
✓ Increase timeout: APIClient(timeout=10)
✓ Check if API server is slow
✓ Check network connection
```

### Falls back to local data
```
✓ Check if API is returning data
✓ Run health_check() to verify API status
✓ Check APIClient logs for errors
```

---

## Summary

| Method | Pros | Cons |
|--------|------|------|
| **Pure API** | Real data, no simulation | Depends on external server |
| **Hybrid** | Real data + fallback | More complex code |
| **API + CSV fallback** | Best reliability | Slightly more overhead |

**Recommended**: Start with **Hybrid Mode** for reliability

---

## Files

- **`data/api_client.py`** - API client implementation
- **`API_INTEGRATION.md`** - This guide
- **`dashboard/app.py`** - Dashboard (modify to use API)

---

**Ready to connect to real data!** 🚀
