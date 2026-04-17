"""
API Client for External Data Integration

Connects to external APIs to fetch:
- Real-time sensor data streams
- Historical data for ML training

Usage:
    from data.api_client import APIClient
    
    client = APIClient(base_url="http://localhost:3000")
    
    # Get live data
    live_data = client.get_live_stream("CNC_01")
    
    # Get historical data
    history = client.get_historical_data("CNC_01")
"""

import requests
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIClient:
    """
    Client for fetching data from external APIs
    
    Supports:
    - Live data stream API
    - Historical data API
    - Error handling and retries
    - Data format normalization
    """
    
    def __init__(self, base_url: str = "http://localhost:3000", timeout: int = 5):
        """
        Initialize API client
        
        Args:
            base_url: Base URL of the API server (e.g., http://localhost:3000)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
    
    def get_live_stream(self, machine_id: str) -> Optional[Dict]:
        """
        Fetch live sensor data for a machine via SSE (Server-Sent Events)
        
        GET /stream/{machine_id}
        
        Connects to SSE endpoint and retrieves ONE sensor reading.
        Automatically maps API keys (temperature, vibration, current)
        to internal format (temperature_C, vibration_mm_s, current_A).
        
        Args:
            machine_id: Machine identifier (e.g., "CNC_01", "PUMP_03")
            
        Returns:
            Dictionary with normalized sensor data:
            {
                "machine_id": "CNC_01",
                "timestamp": "2024-04-17T12:34:56Z",
                "temperature_C": 75.5,
                "vibration_mm_s": 2.1,
                "rpm": 1500,
                "current_A": 15.8,
                "status": "running"
            }
            
        Returns None if request fails
        """
        try:
            url = f"{self.base_url}/stream/{machine_id}"
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Step 1: Read SSE stream line by line
            # SSE format: "data: {json}\n\n"
            for line in response.iter_lines():
                if not line:
                    continue
                
                line = line.decode('utf-8') if isinstance(line, bytes) else line
                
                # Step 2: Parse SSE data line (skip comments, focus on "data:" prefix)
                if line.startswith("data: "):
                    json_str = line[6:]  # Remove "data: " prefix
                    try:
                        data = json.loads(json_str)
                        # Step 3: Normalize keys and return first reading
                        normalized = self._normalize_data(data, machine_id)
                        logger.info(f"✅ Live stream data received for {machine_id}")
                        return normalized
                    except json.JSONDecodeError as e:
                        logger.error(f"📝 Invalid JSON in SSE stream: {e}")
                        continue
            
            logger.warning(f"⚠️ No data received from stream {machine_id}")
            return None
            
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Connection error: Cannot reach {self.base_url}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout: Request to {self.base_url} took too long")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"🔴 HTTP error: {e.response.status_code} - {e.response.reason}")
            return None
        except Exception as e:
            logger.error(f"⚠️ Unexpected error: {str(e)}")
            return None
    
    def get_historical_data(self, machine_id: str, days: int = 7) -> Optional[List[Dict]]:
        """
        Fetch historical sensor data for ML training
        
        GET /history/{machine_id}?days=7
        
        Args:
            machine_id: Machine identifier (e.g., "CNC_01")
            days: Number of days of history to fetch (default: 7)
            
        Returns:
            List of sensor data dictionaries:
            [
                {
                    "machine_id": "CNC_01",
                    "timestamp": "2024-04-10T00:00:00Z",
                    "temperature_C": 72.5,
                    "vibration_mm_s": 1.8,
                    "rpm": 1500,
                    "current_A": 15.2,
                    "status": "running"
                },
                ...
            ]
            
        Returns None if request fails
        """
        try:
            url = f"{self.base_url}/history/{machine_id}"
            params = {"days": days}
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle both list and paginated responses
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict) and "data" in data:
                records = data["data"]
            else:
                logger.warning(f"Unexpected historical data format: {type(data)}")
                records = []
            
            logger.info(f"✅ Historical data received for {machine_id}: {len(records)} records")
            return [self._normalize_data(record, machine_id) for record in records]
            
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Connection error: Cannot reach {self.base_url}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout: Request to {self.base_url} took too long")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"🔴 HTTP error: {e.response.status_code} - {e.response.reason}")
            return None
        except json.JSONDecodeError:
            logger.error(f"📝 Invalid JSON response from {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"⚠️ Unexpected error: {str(e)}")
            return None
    
    def get_all_machines(self) -> Optional[List[str]]:
        """
        Fetch list of available machines
        
        GET /machines
        
        Returns:
            List of machine IDs: ["CNC_01", "CNC_02", ...]
            Returns None if request fails
        """
        try:
            url = f"{self.base_url}/machines"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle various response formats
            if isinstance(data, list):
                machines = data
            elif isinstance(data, dict) and "machines" in data:
                machines = data["machines"]
            else:
                machines = []
            
            logger.info(f"✅ Found {len(machines)} machines")
            return machines
            
        except Exception as e:
            logger.error(f"⚠️ Error fetching machines: {str(e)}")
            return None
    
    def health_check(self) -> bool:
        """
        Check if API server is healthy
        
        Tries multiple endpoints:
        1. GET /health (dedicated health endpoint)
        2. GET /machines (fallback - list machines)
        3. GET /stream/test (fallback - test stream endpoint)
        
        Returns:
            True if server is reachable and responding, False otherwise
        """
        # Strategy 1: Try /health endpoint (dedicated health check)
        try:
            url = f"{self.base_url}/health"
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                logger.info(f"✅ API Server healthy: {self.base_url}")
                return True
        except Exception as e:
            logger.debug(f"Health endpoint not available: {str(e)}")
        
        # Strategy 2: Try /machines endpoint (list machines)
        try:
            url = f"{self.base_url}/machines"
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code in [200, 404]:  # 200 = machines exist, 404 = endpoint exists
                logger.info(f"✅ API Server is accessible via /machines endpoint")
                return True
        except Exception as e:
            logger.debug(f"Machines endpoint not available: {str(e)}")
        
        # Strategy 3: Try /stream endpoint (SSE stream test)
        try:
            url = f"{self.base_url}/stream/test"
            response = self.session.get(url, timeout=self.timeout, stream=True)
            # Even 404 means server is responsive
            if response.status_code in [200, 404, 400]:
                logger.info(f"✅ API Server is responsive via /stream endpoint")
                return True
        except Exception as e:
            logger.debug(f"Stream endpoint not accessible: {str(e)}")
        
        # If all strategies failed, server is unreachable
        logger.error(f"❌ API Server unreachable: {self.base_url}")
        return False
    
    def send_alert(
        self,
        machine_id: str,
        severity: str,
        reason: str,
        reading: Optional[Dict] = None
    ) -> bool:
        """
        Send critical alert to API server
        
        POST /alert
        
        Called when AI Agent detects CRITICAL condition.
        Sends alert with machine_id, severity, reason, and current reading.
        
        Args:
            machine_id: Machine identifier (e.g., "CNC_01")
            severity: Alert severity ("CRITICAL", "WARNING", "WATCH")
            reason: Human-readable description (e.g., "Temperature exceeding 90°C")
            reading: Current sensor reading dict (optional)
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        try:
            url = f"{self.base_url}/alert"
            payload = {
                "machine_id": machine_id,
                "severity": severity,
                "reason": reason,
                "timestamp": self._utc_now(),
                "reading": reading or {}
            }
            
            response = self.session.post(url, json=payload, timeout=self.timeout)
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"✅ {severity} alert sent for {machine_id}: {reason}")
                return True
            else:
                logger.warning(f"⚠️ Alert POST returned {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot send alert: Connection to {self.base_url} failed")
            return False
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Cannot send alert: Request timeout")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send alert: {str(e)}")
            return False
    
    def _normalize_data(self, data: Dict, machine_id: str = None) -> Dict:
        """
        Normalize data to standard internal format
        
        Maps API response keys to internal canonical format:
        - API: temperature      → Internal: temperature_C
        - API: vibration        → Internal: vibration_mm_s
        - API: rpm              → Internal: rpm
        - API: current          → Internal: current_A
        
        Also converts various timestamp formats to ISO 8601 UTC format.
        
        Args:
            data: Raw API response data
            machine_id: Machine identifier (optional, taken from data if not provided)
            
        Returns:
            Normalized dict with standard keys ready for preprocessing and ML
        """
        # Extract machine_id from data or parameter
        final_machine_id = machine_id or data.get("machine_id", "UNKNOWN")
        
        # Try multiple key names for each sensor (API may use different names)
        normalized = {
            "machine_id": final_machine_id,
            "timestamp": data.get("timestamp", self._utc_now()),
            # Temperature: try both API format and internal format
            "temperature_C": float(data.get("temperature_C", data.get("temperature", 0))),
            # Vibration: try both API format and internal format
            "vibration_mm_s": float(data.get("vibration_mm_s", data.get("vibration", 0))),
            # RPM: consistent across formats
            "rpm": float(data.get("rpm", 0)),
            # Current: try both API format and internal format
            "current_A": float(data.get("current_A", data.get("current", 0))),
            # Status: optional, defaults to "running"
            "status": data.get("status", "running"),
        }
        
        return normalized
    
    def _utc_now(self) -> str:
        """Get current UTC timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup"""
        self.session.close()


# Convenience function
def create_client(base_url: str = "http://localhost:3000") -> APIClient:
    """Create and return an API client instance"""
    return APIClient(base_url=base_url)
