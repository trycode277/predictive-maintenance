import pandas as pd
from sklearn.ensemble import IsolationForest


FEATURE_COLUMNS = ["temperature_C", "vibration_mm_s", "rpm", "current_A"]
LEGACY_SENSOR_MAP = {
    "temp_1": "temperature_C",
    "vibration_1": "vibration_mm_s",
    "rpm_1": "rpm",
    "current_1": "current_A",
}


class AnomalyModel:
    def __init__(self):
        self.model = IsolationForest(contamination=0.05, random_state=42)
        self.trained = False

    def _coerce_frame(self, payload):
        df = pd.DataFrame(payload).copy()
        df = df.rename(columns=LEGACY_SENSOR_MAP)

        for column in FEATURE_COLUMNS:
            if column not in df.columns:
                df[column] = 0.0

        return df[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    def train(self, historical_data):
        features = self._coerce_frame(historical_data)
        if features.empty:
            return

        self.model.fit(features)
        self.trained = True

    def predict(self, sensors):
        if not self.trained:
            return False

        features = self._coerce_frame([sensors])
        result = self.model.predict(features)
        return result[0] == -1

    def anomaly_score(self, sensors):
        if not self.trained:
            return 0.0

        features = self._coerce_frame([sensors])
        return float(-self.model.decision_function(features)[0])
