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
        Fetch live sensor data for a machine
        
        GET /stream/{machine_id}
        
        Args:
            machine_id: Machine identifier (e.g., "CNC_01")
            
        Returns:
            Dictionary with sensor data:
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
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Live stream data received for {machine_id}")
            return self._normalize_data(data)
            
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
            return [self._normalize_data(record) for record in records]
            
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
        
        GET /health
        
        Returns:
            True if server is reachable, False otherwise
        """
        try:
            url = f"{self.base_url}/health"
            response = self.session.get(url, timeout=self.timeout)
            is_healthy = response.status_code == 200
            
            if is_healthy:
                logger.info(f"✅ API Server healthy: {self.base_url}")
            else:
                logger.warning(f"⚠️ API Server returned status {response.status_code}")
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"❌ API Server unreachable: {str(e)}")
            return False
    
    def _normalize_data(self, data: Dict) -> Dict:
        """
        Normalize data to standard format
        
        Converts various timestamp and field formats to standard format
        """
        normalized = {
            "machine_id": data.get("machine_id", "UNKNOWN"),
            "timestamp": data.get("timestamp", self._utc_now()),
            "temperature_C": float(data.get("temperature_C", data.get("temperature", 0))),
            "vibration_mm_s": float(data.get("vibration_mm_s", data.get("vibration", 0))),
            "rpm": float(data.get("rpm", 0)),
            "current_A": float(data.get("current_A", data.get("current", 0))),
            "status": data.get("status", "unknown"),
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
