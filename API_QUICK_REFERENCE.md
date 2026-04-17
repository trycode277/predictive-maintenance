# 🌐 API Quick Reference

## Test APIs Without Code

### PowerShell
```powershell
# Live data
curl http://localhost:3000/stream/CNC_01

# Historical data
curl "http://localhost:3000/history/CNC_01?days=7"

# Machines list
curl http://localhost:3000/machines

# Health check
curl http://localhost:3000/health
```

### Browser
```
http://localhost:3000/stream/CNC_01
http://localhost:3000/history/CNC_01?days=7
http://localhost:3000/machines
http://localhost:3000/health
```

---

## API Quick Start (5 minutes)

### Step 1: Test Connection
```python
from data.api_client import APIClient

client = APIClient(base_url="http://localhost:3000")
print("✅ Connected!" if client.health_check() else "❌ Connection failed")
```

### Step 2: Get Live Data
```python
data = client.get_live_stream("CNC_01")
print(data)
```

### Step 3: Use in Dashboard
```python
# In dashboard/app.py, in advance_stream():

client = APIClient(base_url="http://localhost:3000")

snapshot = []
for machine_id in MACHINE_IDS:
    data = client.get_live_stream(machine_id)
    if data:
        snapshot.append(data)
```

---

## API Endpoints

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/stream/{id}` | GET | Single sensor reading |
| `/history/{id}?days=7` | GET | 7 days of history |
| `/machines` | GET | List of machine IDs |
| `/health` | GET | Server status |

---

## Data Format

**Live Data** (one reading):
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

**Historical Data** (array):
```json
[
    {...},
    {...},
    ...
]
```

---

## Common Issues & Fixes

| Problem | Fix |
|---------|-----|
| "Cannot reach API" | Check API server is running on :3000 |
| "Connection refused" | Verify port 3000 is not blocked |
| "Invalid JSON" | API returned malformed data |
| "Timeout" | API is slow, increase timeout |

---

## Code Examples

### Get Data for One Machine
```python
from data.api_client import APIClient

client = APIClient("http://localhost:3000")
data = client.get_live_stream("CNC_01")
```

### Get Data for All Machines
```python
machines = client.get_all_machines()
for machine in machines:
    data = client.get_live_stream(machine)
    print(f"{machine}: {data['temperature_C']}°C")
```

### Get Historical Data
```python
history = client.get_historical_data("CNC_01", days=7)
print(f"Got {len(history)} records")
```

### With Error Handling
```python
client = APIClient("http://localhost:3000")

if not client.health_check():
    print("API is down, using local data")
else:
    data = client.get_live_stream("CNC_01")
    if data:
        print("Got API data")
```

---

## Run Examples

```bash
cd c:\Users\dayan\predictive-maintenance
python examples/api_examples.py
```

Shows:
- ✅ API connection test
- ✅ Live data fetch
- ✅ Machine list
- ✅ Historical data
- ✅ All machines loop
- ✅ API vs Local comparison

---

## Files

| File | Purpose |
|------|---------|
| `data/api_client.py` | API client library |
| `API_INTEGRATION.md` | Full integration guide |
| `examples/api_examples.py` | Code examples |
| `API_QUICK_REFERENCE.md` | This file |

---

## Integration Paths

### Option A: Replace Local Data
```python
# Before
snapshot = get_live_snapshot(MACHINE_IDS)

# After
client = APIClient("http://localhost:3000")
snapshot = [client.get_live_stream(m) for m in MACHINE_IDS]
```

### Option B: Hybrid (API + Fallback)
```python
data = client.get_live_stream(machine)
if not data:
    # Fallback to local
    data = get_live_snapshot([machine])[0]
```

### Option C: Use for Historical Only
```python
# Live: Use local simulation
# Historical: Use API
history = client.get_historical_data(machine, days=7)
```

---

## Next Steps

1. **Test APIs** - Use curl or browser
2. **Run examples** - `python examples/api_examples.py`
3. **Choose integration** - Pick option A, B, or C
4. **Modify dashboard** - Update `advance_stream()`
5. **Test with real data** - Start your API server

---

**That's it! You're ready to connect to real data.** 🚀
