# 🔧 AI Agent Configuration Guide

## Quick Configuration

### 1. Adjust Temperature Thresholds

**File**: `agent/decision_agent.py` → `rule_engine()` method

```python
def rule_engine(self, data):
    # Temperature rules
    CRITICAL_TEMP = 95      # ← Change this
    WARNING_TEMP = 85       # ← Or this
    
    if data.get("temperature_C", 0) > CRITICAL_TEMP:
        return "CRITICAL_TEMPERATURE"
    if data.get("temperature_C", 0) > WARNING_TEMP:
        return "HIGH_TEMPERATURE"
```

### 2. Adjust Vibration Thresholds

```python
    CRITICAL_VIB = 3.0      # ← Change this
    WARNING_VIB = 2.0       # ← Or this
    
    if data.get("vibration_mm_s", 0) > CRITICAL_VIB:
        return "CRITICAL_VIBRATION"
    if data.get("vibration_mm_s", 0) > WARNING_VIB:
        return "HIGH_VIBRATION"
```

### 3. Adjust Current Thresholds

```python
    CRITICAL_AMP = 18       # ← Change this
    WARNING_AMP = 16        # ← Or this
    
    if data.get("current_A", 0) > CRITICAL_AMP:
        return "CRITICAL_CURRENT"
    if data.get("current_A", 0) > WARNING_AMP:
        return "HIGH_CURRENT"
```

### 4. Adjust RPM Thresholds

```python
    HIGH_RPM = 1700         # ← Change this
    LOW_RPM = 1250          # ← Or this
    
    if data.get("rpm", 0) > HIGH_RPM:
        return "HIGH_RPM"
    if data.get("rpm", 0) < LOW_RPM:
        return "LOW_RPM"
```

---

## Decision Level Configuration

### Current Decision Matrix

| Condition | Decision | Action |
|-----------|----------|--------|
| CRITICAL rule violation | CRITICAL | AUTO_SHUTDOWN |
| ML score < -0.5 | CRITICAL | AUTO_SHUTDOWN |
| HIGH rule violation | WARNING | ALERT_MAINTENANCE |
| ML anomaly detected | WARNING | ALERT_MAINTENANCE |
| Patterns detected | WATCH | INCREASE_MONITORING |
| All normal | NORMAL | CONTINUE_NORMAL |

**To modify**: Edit `make_decision()` method in `decision_agent.py`

---

## Recommendation Customization

### Current Recommendations

**CRITICAL:**
- Temperature: "CRITICAL: Temperature exceeds safe limits..."
- Vibration: "CRITICAL: Abnormal vibration detected..."
- Current: "CRITICAL: Electrical current too high..."

**WARNING:**
- Temperature: "WARNING: Temperature rising..."
- Vibration: "WARNING: Elevated vibration..."
- Current: "WARNING: Current draw increasing..."

**WATCH:**
- "WATCH: Minor anomalies detected..."

**NORMAL:**
- "NORMAL: Machine operating within expected parameters."

**To modify**: Edit `generate_recommendation()` method in `decision_agent.py`

---

## Advanced Configuration

### 1. Add New Rule Type

```python
def rule_engine(self, data):
    # ... existing rules ...
    
    # NEW RULE
    if data.get("new_sensor", 0) > 100:
        return "NEW_SENSOR_VIOLATION"
    
    return None
```

### 2. Handle New Rule in Decision

```python
def make_decision(self, score, prediction, rule_violation):
    if rule_violation == "NEW_SENSOR_VIOLATION":
        return "WARNING"  # or "CRITICAL"
    # ... rest of logic ...
```

### 3. Add Recommendation for New Rule

```python
def generate_recommendation(self, data, decision, rule_violation):
    if decision == "WARNING":
        if rule_violation == "NEW_SENSOR_VIOLATION":
            return "WARNING: New sensor exceeded threshold. Check..."
        # ... other recommendations ...
```

---

## ML Model Adjustment

### Anomaly Score Threshold

**Current**: score < -0.5 for CRITICAL

```python
def make_decision(self, score, prediction, rule_violation):
    if prediction == -1:  # Anomaly detected
        if score < -0.5:  # ← Change this threshold
            return "CRITICAL"
        else:
            return "WARNING"
```

**Options**:
- More aggressive: Change -0.5 to -0.3
- Less aggressive: Change -0.5 to -0.7

---

## Dashboard Configuration

### Agent Metrics Color Scheme

**File**: `dashboard/app.py` → `render_agent_insights()` function

```python
decision_colors = {
    "CRITICAL": "#ff8c7b",      # ← Red
    "WARNING": "#f4c152",       # ← Yellow
    "WATCH": "#66dbff",         # ← Cyan
    "NORMAL": "#4fdb96",        # ← Green
    "OFFLINE": "#97a6c5",       # ← Gray
}
```

---

## Testing Configuration Changes

### 1. Syntax Check
```bash
cd c:\Users\dayan\predictive-maintenance
python -m py_compile agent/decision_agent.py dashboard/app.py
```

### 2. Manual Testing
```python
from agent.decision_agent import DecisionAgent
from models.isolation_forest import AnomalyModel

model = AnomalyModel()
agent = DecisionAgent(model)

# Test data
test_data = {
    "temperature_C": 92,
    "vibration_mm_s": 2.5,
    "current_A": 16.8,
    "rpm": 1500
}

result = agent.analyze(test_data, machine_id="TEST_MACHINE")
print(f"Decision: {result['decision']}")
print(f"Recommendation: {result['recommendation']}")
print(f"Action: {result['action']}")
```

---

## Common Configurations

### Strict Mode (More Alerts)
```python
# Lower all thresholds
CRITICAL_TEMP = 90      # Was 95
WARNING_TEMP = 80       # Was 85
CRITICAL_VIB = 2.5      # Was 3.0
WARNING_VIB = 1.5       # Was 2.0
ML_THRESHOLD = -0.7     # Was -0.5 (more conservative)
```

### Relaxed Mode (Fewer Alerts)
```python
# Raise all thresholds
CRITICAL_TEMP = 100     # Was 95
WARNING_TEMP = 90       # Was 85
CRITICAL_VIB = 3.5      # Was 3.0
WARNING_VIB = 2.5       # Was 2.0
ML_THRESHOLD = -0.3     # Was -0.5 (more aggressive)
```

### Balanced Mode (Current)
```python
# Well-tuned thresholds
CRITICAL_TEMP = 95
WARNING_TEMP = 85
CRITICAL_VIB = 3.0
WARNING_VIB = 2.0
ML_THRESHOLD = -0.5
```

---

## Performance Tuning

### Action Log Size
**File**: `agent/decision_agent.py` → `log_action()` method

```python
def log_action(self, result):
    self.action_log.append(result)
    if len(self.action_log) > 1000:  # ← Change buffer size
        self.action_log = self.action_log[-1000:]
```

**Options**:
- Memory-constrained: Use 100-500
- Normal: Use 1000 (current)
- Archive-heavy: Use 5000+

---

## Integration Points

### Custom Shutdown Handler
```python
def determine_action(self, decision, rule_violation):
    if decision == "CRITICAL":
        return "AUTO_SHUTDOWN"
        # TODO: Add your custom shutdown code here
        # e.g., send_to_plc(), send_email_alert(), etc.
```

### Custom Notification
```python
def log_action(self, result):
    self.action_log.append(result)
    
    # TODO: Add custom notification
    # e.g., send_slack_message(result), send_to_webhook(), etc.
    
    if len(self.action_log) > 1000:
        self.action_log = self.action_log[-1000:]
```

---

## Validation Checklist

Before going to production, verify:

- [ ] Thresholds reviewed with operations team
- [ ] Recommendation texts approved
- [ ] Color scheme tested with team
- [ ] Action codes mapped to hardware/systems
- [ ] Logging configured appropriately
- [ ] Performance tested with full load
- [ ] Staff trained on new features
- [ ] Fallback procedures documented

---

## Troubleshooting

### Agent Always Returns NORMAL
- Check if ML model is trained correctly
- Verify thresholds are appropriate
- Check sensor data is being collected

### Too Many CRITICAL Alerts
- Increase thresholds (less aggressive)
- Adjust ML score threshold (-0.5 → -0.3)
- Review sensor calibration

### Agent Decisions Don't Match Manual Review
- Compare against rule engine logic
- Check threshold values
- Verify ML model performance
- Review recent configuration changes

---

## Monitoring the Agent

### Check Decision Distribution
```python
from collections import Counter

decisions = [action['decision'] for action in agent.action_log]
distribution = Counter(decisions)
print(distribution)
# Output: Counter({'WARNING': 15, 'CRITICAL': 8, 'NORMAL': 2})
```

### Get Alert Statistics
```python
critical_count = sum(1 for a in agent.action_log if a['decision'] == 'CRITICAL')
warning_count = sum(1 for a in agent.action_log if a['decision'] == 'WARNING')
print(f"Critical: {critical_count}, Warning: {warning_count}")
```

---

**Configuration Last Updated**: 2024
**Agent Version**: 1.0
