import json
import requests
from typing import Dict, List, Optional, Any
import streamlit as st
from datetime import datetime, timezone

class ApiDataLoader:
    def __init__(
        self,
        base_url: str,
        endpoint: str = '/api/sensor-data',
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        request_payload: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 2
    ):
        self.session = requests.Session()
        self.base_url = base_url.rstrip('/')
        self.endpoint = endpoint.lstrip('/')
        self.url = f'{self.base_url}/{self.endpoint}'
        self.method = method.upper()
        self.default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            **(headers or {})
        }
        self.request_payload = json.loads(request_payload) if request_payload else None
        self.timeout = timeout
        self.max_retries = max_retries

    def _make_request(self) -> Optional[Dict[str, Any]]:
        for attempt in range(self.max_retries + 1):
            try:
                if self.method == 'GET':
                    resp = self.session.get(self.url, headers=self.default_headers, timeout=self.timeout)
                elif self.method == 'POST':
                    resp = self.session.post(
                        self.url,
                        headers=self.default_headers,
                        json=self.request_payload,
                        timeout=self.timeout
                    )
                else:
                    st.error(f"Unsupported method: {self.method}. Use GET or POST.")
                    return None

                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries:
                    st.error(f"API request failed after {self.max_retries} retries: {str(e)}")
                    return None
                continue
        return None

    def fetch_live_snapshot(self, machine_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch live machine data from API. Returns list[dict] matching local schema:
        {'machine_id', 'timestamp'(ISO Z), 'temperature_C', 'vibration_mm_s', 'rpm', 'current_A', 'status'}
        Filters invalid records.
        """
        data = self._make_request()
        if not data or not isinstance(data, list):
            st.warning("API returned empty/invalid list. Falling back to no data.")
            return []

        valid_records = []
        required_keys = {'machine_id', 'timestamp', 'temperature_C', 'vibration_mm_s', 'rpm', 'current_A', 'status'}

        for record in data:
            if not isinstance(record, dict):
                continue
            # Check required keys (flexible: extra keys OK)
            if required_keys.issubset(record.keys()):
                # Normalize timestamp if needed
                ts = record.get('timestamp')
                if ts and not ts.endswith('Z'):
                    try:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        record['timestamp'] = dt.isoformat().replace('+00:00', 'Z')
                    except:
                        pass
                valid_records.append(record)
            else:
                st.warning(f"Skipping invalid record (missing keys): {list(record.keys())}")

        if machine_ids:
            valid_records = [r for r in valid_records if r.get('machine_id') in machine_ids]

        st.info(f"API fetched {len(valid_records)} valid records.")
        return valid_records

