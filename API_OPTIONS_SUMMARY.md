# 📚 API Integration Complete - Your Options

## What You Have Now

### ✅ Created Files

1. **`data/api_client.py`** - API Client Library
   - Fetch live data
   - Fetch historical data
   - Health checks
   - Error handling
   - Data normalization

2. **`API_INTEGRATION.md`** - Complete Guide
   - Full documentation
   - How each API works
   - Integration examples
   - Error handling

3. **`API_QUICK_REFERENCE.md`** - Quick Lookup
   - API endpoints
   - Code snippets
   - Common issues
   - Test commands

4. **`INTEGRATION_STEPS.md`** - Step-by-Step Guide
   - 5-minute quick setup
   - 3 integration methods
   - Code you can copy-paste
   - Testing checklist

5. **`examples/api_examples.py`** - Working Examples
   - Test API connection
   - Get live data
   - Get historical data
   - Loop all machines
   - Continuous streaming

---

## Your Options

### Option 1: Pure API ⭐ (Simplest)
```
┌─────────────────┐
│  External API   │
│  (Real Data)    │
└────────┬────────┘
         │
┌────────▼────────┐
│   Dashboard     │
│  (Uses API)     │
└─────────────────┘
```

**Pros:**
- Real data only
- Simplest code
- No simulation

**Cons:**
- Depends on API availability
- If API down, no data

**Use When:** API is always reliable

---

### Option 2: Hybrid (Recommended) ⭐⭐⭐ (Best)
```
┌──────────────────────┐
│  External API Server │
│    (Real Data)       │
└────────────┬─────────┘
             │
      ┌──────▼──────┐
      │API Available?
      └──────┬───┬──┘
         Yes │   │ No
      ┌──────▼─┐ │
      │   API  │ │
      └────────┘ │
                 │
      ┌──────────▼──────┐
      │ Local Simulation│
      │  (Fallback)     │
      └─────────┬───────┘
               │
      ┌────────▼────────┐
      │   Dashboard     │
      │ (Real or Demo)  │
      └─────────────────┘
```

**Pros:**
- Real data when available
- Demo data when API down
- Most reliable

**Cons:**
- Slightly more code

**Use When:** Want best of both worlds

---

### Option 3: Split (Mixed) ⭐⭐ (Balanced)
```
┌──────────────────┐
│  External API    │
│  (Historical)    │
└────────┬─────────┘
         │
         └──────────┬─────────┐
                    │         │
                    │    ┌────▼──────────┐
         ┌──────────┘    │ Local Simulation
         │               │ (Live Data)
    ┌────▼─────────────┐ │
    │   Dashboard      │ │
    │ (Best of Both)   │ │
    └──────────────────┘ │
                         └────────────────┘
```

**Pros:**
- Real historical data (ML)
- Fast live data (local)
- Best performance

**Cons:**
- API only used for history

**Use When:** Want real ML training data + fast live updates

---

## Quick Start (Choose One)

### If You Want: Pure API (All Real Data)
```bash
# 1. Edit dashboard/app.py
# 2. Add this at top:
from data.api_client import APIClient
API_CLIENT = APIClient(base_url="http://localhost:3000")

# 3. Replace advance_stream() - see INTEGRATION_STEPS.md - Method 1
# 4. Test:
python -m py_compile dashboard/app.py
streamlit run dashboard/app.py
```

---

### If You Want: Hybrid (Recommended)
```bash
# 1. Edit dashboard/app.py
# 2. Add this at top:
from data.api_client import APIClient
API_CLIENT = APIClient(base_url="http://localhost:3000")
API_HEALTHY = False

# 3. Replace advance_stream() - see INTEGRATION_STEPS.md - Method 2
# 4. Test:
python -m py_compile dashboard/app.py
streamlit run dashboard/app.py
```

---

### If You Want: Split (Historical from API)
```bash
# 1. Keep advance_stream() as is
# 2. Edit dashboard/app.py
# 3. Add this at top:
from data.api_client import APIClient
API_CLIENT = APIClient(base_url="http://localhost:3000")

# 4. Replace load_historical_frame() - see INTEGRATION_STEPS.md - Method 3
# 5. Test:
python -m py_compile dashboard/app.py
streamlit run dashboard/app.py
```

---

## Test First (Important!)

### Step 1: Verify API is Running
```bash
# PowerShell
curl http://localhost:3000/stream/CNC_01

# Should return JSON:
# {"machine_id":"CNC_01","temperature_C":75.5,...}
```

### Step 2: Run Examples
```bash
cd c:\Users\dayan\predictive-maintenance
python examples/api_examples.py
```

**Shows:**
- ✅ Connection test
- ✅ Live data fetch
- ✅ Machine list
- ✅ Historical data
- ✅ All machines
- ✅ API vs Local comparison

### Step 3: Syntax Check
```bash
python -m py_compile dashboard/app.py
```

**Result:**
- ✅ No output = Success
- ❌ Error = Fix and retry

### Step 4: Run Dashboard
```bash
streamlit run dashboard/app.py
```

**Verify:**
- ✅ Dashboard loads
- ✅ Data appears
- ✅ Agent decisions work
- ✅ No errors in console

---

## What Each File Does

| File | Purpose | Read When |
|------|---------|-----------|
| `data/api_client.py` | API library code | You want to see implementation |
| `API_INTEGRATION.md` | Full guide | You need complete documentation |
| `API_QUICK_REFERENCE.md` | Quick lookup | You need a command/example fast |
| `INTEGRATION_STEPS.md` | Step-by-step | You're ready to integrate |
| `examples/api_examples.py` | Working code | You want to test before integrating |

---

## The Connection Flow

```
Your Machines (Real World)
        │
        │ (MQTT, Kafka, REST, etc.)
        ▼
API Server (http://localhost:3000)
        │
        │ (HTTP Request)
        ▼
API Client (data/api_client.py)
        │
        │ (Fetch & Normalize)
        ▼
Dashboard (dashboard/app.py)
        │
        ├─ Preprocessing
        ├─ Buffering
        ├─ ML Analysis
        ├─ AI Agent Decision
        └─ Visualization
        │
        ▼
Browser Display
   (Your Dashboard!)
```

---

## Which Method Should You Choose?

```
                  ┌─────────────────────────────────┐
                  │ Is API always reliable?         │
                  └────┬────────────────────────┬───┘
                      YES                        NO
                       │                         │
                  ┌────▼──────┐        ┌────────▼──────┐
                  │ Pure API   │        │ Hybrid Method │
                  │ (Option 1) │        │ (Option 2)    │
                  └────────────┘        └────────────────┘
                                               │
                  ┌────────────────────────────┘
                  │
                  │ Want real historical data?
                  ├─ Yes → Use Split (Option 3)
                  └─ No → Use Hybrid (Option 2)
```

**My Recommendation:**
- **Start with**: Hybrid (Option 2)
- **Why**: Most reliable, easy to test, works when API is down
- **Later**: Switch to Pure API (Option 1) if API is stable

---

## Cheat Sheet

### Import API Client
```python
from data.api_client import APIClient
API_CLIENT = APIClient(base_url="http://localhost:3000")
```

### Get Live Data
```python
data = API_CLIENT.get_live_stream("CNC_01")
```

### Get Historical Data
```python
history = API_CLIENT.get_historical_data("CNC_01", days=7)
```

### Check Health
```python
if API_CLIENT.health_check():
    print("✅ API is up")
```

### Get All Machines
```python
machines = API_CLIENT.get_all_machines()
```

---

## Files You'll Edit

| File | Action |
|------|--------|
| `dashboard/app.py` | Modify `advance_stream()` or `load_historical_frame()` |
| Nothing else | Just add API client code to one function |

---

## Common Edits at a Glance

### Add Import (Top of dashboard/app.py)
```python
from data.api_client import APIClient
API_CLIENT = APIClient(base_url="http://localhost:3000")
```

### Simple Replacement (One Function)
Old:
```python
def advance_stream():
    snapshot = get_live_snapshot(MACHINE_IDS)
```

New:
```python
def advance_stream():
    snapshot = []
    for m in MACHINE_IDS:
        d = API_CLIENT.get_live_stream(m)
        if d: snapshot.append(d)
    if not snapshot:
        snapshot = get_live_snapshot(MACHINE_IDS)
```

---

## Next Steps

1. **Today**: Test APIs with curl or browser
2. **Today**: Run `python examples/api_examples.py`
3. **Today**: Choose your integration method
4. **Tomorrow**: Modify dashboard/app.py
5. **Tomorrow**: Test with `python -m py_compile`
6. **Tomorrow**: Run dashboard and verify
7. **Next Week**: Monitor and adjust

---

## Support

**Can't connect?**
- Check API server is running on :3000
- Try: `curl http://localhost:3000/health`
- Read: INTEGRATION_STEPS.md - Troubleshooting

**Need code?**
- See: INTEGRATION_STEPS.md - Quick Copy-Paste

**Want full details?**
- Read: API_INTEGRATION.md (Complete guide)

**Want examples?**
- Run: `python examples/api_examples.py`

---

## Summary

✅ **You have everything to connect to real data**

✅ **Choose method**: Pure, Hybrid, or Split

✅ **Follow steps**: INTEGRATION_STEPS.md is your guide

✅ **Test first**: examples/api_examples.py

✅ **Make small change**: One function in dashboard/app.py

✅ **Verify it works**: Test with dashboard

**That's it! Real data in hours, not days.** 🚀

---

**Ready?** Pick a method and follow INTEGRATION_STEPS.md!
