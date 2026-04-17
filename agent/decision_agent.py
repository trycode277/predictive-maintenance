import logging
from datetime import datetime


class DecisionAgent:
    """
    Intelligent Decision Agent for Predictive Maintenance
    
    Combines ML anomaly detection, rule-based logic, and decision making
    to provide actionable recommendations for machine maintenance.
    
    Features:
    - ML-based anomaly detection
    - Rule engine for threshold violations
    - Intelligent decision making (CRITICAL/WARNING/WATCH/NORMAL)
    - Automatic action determination
    - Detailed recommendations
    """
    
    def __init__(self, model):
        self.model = model
        self.action_log = []
        self.logger = logging.getLogger(__name__)

    def analyze(self, data, machine_id=None):
        """
        Comprehensive analysis: ML + Rules + Decision + Recommendation
        
        Args:
            data: Dictionary containing sensor data
            machine_id: Optional machine identifier
            
        Returns:
            Dictionary with analysis results including:
            - score: ML anomaly score
            - prediction: ML anomaly prediction (-1 for anomaly, 1 for normal)
            - decision: Decision level (CRITICAL/WARNING/WATCH/NORMAL)
            - recommendation: Actionable recommendation text
            - action: Automatic action to take
            - rule_violation: Specific rule violation if any
        """
        score = self.model.anomaly_score(data)
        prediction = self.model.predict(data)

        # Apply rule engine
        rule_violation = self.rule_engine(data)
        
        # Make decision combining ML and rules
        decision = self.make_decision(score, prediction, rule_violation)
        
        # Generate recommendation
        recommendation = self.generate_recommendation(data, decision, rule_violation)
        
        # Determine action
        action = self.determine_action(decision, rule_violation)
        
        result = {
            "score": score,
            "prediction": prediction,
            "decision": decision,
            "recommendation": recommendation,
            "action": action,
            "rule_violation": rule_violation,
            "machine_id": machine_id,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Log critical and warning decisions
        if decision in ["CRITICAL", "WARNING"]:
            self.log_action(result)
        
        return result

    def rule_engine(self, data):
        """
        Rule-based logic to detect specific issues
        
        Checks sensor values against defined thresholds.
        Returns the violated rule or None if all rules pass.
        
        Rules checked:
        - Temperature thresholds (critical: >95°C, warning: >85°C)
        - Vibration thresholds (critical: >3.0 mm/s, warning: >2.0 mm/s)
        - Current thresholds (critical: >18A, warning: >16A)
        - RPM thresholds (high: >1700, low: <1250)
        """
        # Temperature rules
        if data.get("temperature_C", 0) > 95:
            return "CRITICAL_TEMPERATURE"
        if data.get("temperature_C", 0) > 85:
            return "HIGH_TEMPERATURE"
        
        # Vibration rules
        if data.get("vibration_mm_s", 0) > 3.0:
            return "CRITICAL_VIBRATION"
        if data.get("vibration_mm_s", 0) > 2.0:
            return "HIGH_VIBRATION"
        
        # Current rules
        if data.get("current_A", 0) > 18:
            return "CRITICAL_CURRENT"
        if data.get("current_A", 0) > 16:
            return "HIGH_CURRENT"
        
        # RPM rules
        if data.get("rpm", 0) > 1700:
            return "HIGH_RPM"
        if data.get("rpm", 0) < 1250:
            return "LOW_RPM"
        
        return None

    def make_decision(self, score, prediction, rule_violation=None):
        """
        Decision logic combining ML anomaly score and rule violations
        
        Priority order:
        1. Rule violations (CRITICAL rules take highest priority)
        2. ML anomaly detection with score analysis
        3. Rule violations at WARNING level
        4. Default to NORMAL
        
        Returns: CRITICAL, WARNING, WATCH, or NORMAL
        """
        # Handle case where rule_violation is passed as parameter (legacy compatibility)
        if rule_violation is None:
            rule_violation = None
        
        # Rule violations take highest priority
        if rule_violation and "CRITICAL" in rule_violation:
            return "CRITICAL"
        
        # ML prediction + score analysis
        if prediction == -1:  # Anomaly detected
            if score < -0.5:
                return "CRITICAL"
            else:
                return "WARNING"
        
        # Rule violations at warning level
        if rule_violation and "HIGH" in rule_violation:
            return "WARNING"
        
        return "NORMAL"

    def generate_recommendation(self, data, decision, rule_violation=None):
        """
        Generate actionable recommendations based on decision and rule violations
        
        Returns specific, actionable text based on the type of issue detected.
        """
        if decision == "CRITICAL":
            if rule_violation == "CRITICAL_TEMPERATURE":
                return "CRITICAL: Temperature exceeds safe limits. Immediate shutdown required. Check cooling system."
            elif rule_violation == "CRITICAL_VIBRATION":
                return "CRITICAL: Abnormal vibration detected. Stop machine immediately. Inspect bearings and alignment."
            elif rule_violation == "CRITICAL_CURRENT":
                return "CRITICAL: Electrical current too high. Shutdown required. Check motor load and connections."
            else:
                return "CRITICAL: Anomaly detected. Immediate shutdown required. Inspect machine thoroughly."
        
        elif decision == "WARNING":
            if rule_violation == "HIGH_TEMPERATURE":
                return "WARNING: Temperature rising. Schedule maintenance within 24 hours. Monitor cooling system."
            elif rule_violation == "HIGH_VIBRATION":
                return "WARNING: Elevated vibration. Plan bearing inspection and balancing check."
            elif rule_violation == "HIGH_CURRENT":
                return "WARNING: Current draw increasing. Review motor load and electrical connections."
            else:
                return "WARNING: Anomaly pattern detected. Schedule maintenance check soon."
        
        elif decision == "WATCH":
            return "WATCH: Minor anomalies detected. Continue monitoring. Plan routine maintenance."
        
        else:
            return "NORMAL: Machine operating within expected parameters."

    def determine_action(self, decision, rule_violation=None):
        """
        Determine automatic action based on decision
        
        Returns action codes that can be used for automation:
        - AUTO_SHUTDOWN: Immediate system shutdown required
        - ALERT_MAINTENANCE: Alert for urgent maintenance
        - INCREASE_MONITORING: Increase monitoring frequency
        - CONTINUE_NORMAL: Normal operation
        """
        if decision == "CRITICAL":
            return "AUTO_SHUTDOWN"
        elif decision == "WARNING":
            return "ALERT_MAINTENANCE"
        elif decision == "WATCH":
            return "INCREASE_MONITORING"
        else:
            return "CONTINUE_NORMAL"

    def log_action(self, result):
        """
        Log critical and warning decisions for audit trail
        """
        self.action_log.append(result)
        if len(self.action_log) > 1000:  # Keep last 1000 actions
            self.action_log = self.action_log[-1000:]
        
        self.logger.warning(
            f"Agent Action: {result['decision']} for {result.get('machine_id', 'unknown')} - "
            f"{result['recommendation']}"
        )

    def get_action_history(self, machine_id=None):
        """
        Get action history, optionally filtered by machine_id
        """
        if machine_id:
            return [a for a in self.action_log if a.get('machine_id') == machine_id]
        return self.action_log.copy()