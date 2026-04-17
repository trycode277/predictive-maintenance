"""
🔥 SSE API Client - Real-time Parallel Stream Listener

Connects to all machines in parallel using Server-Sent Events (SSE)

Architecture:
    CNC_01 ─┐
    CNC_02 ─┼──→ AI Agent → Decision → Alert
    PUMP_03 ─┤
    CONVEYOR─┘

Key Concept:
- /stream/{machine_id} returns SSE (not REST)
- One stream per machine
- Must run all streams in parallel (threading)
- Each stream has its own thread

Usage:
    from data.api_stream_client import StreamAPIClient
    
    client = StreamAPIClient(base_url="http://localhost:3000")
    
    # Listen to all machines with callback
    def on_data(machine_id, data):
        print(f"{machine_id}: {data['temperature_C']}°C")
    
    client.listen_all_machines(
        ["CNC_01", "CNC_02", "PUMP_03", "CONVEYOR_04"],
        callback=on_data
    )
"""

import requests
import json
import logging
import threading
import datetime
from typing import Optional, List, Dict, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamAPIClient:
    """
    Client for connecting to SSE (Server-Sent Events) API streams
    
    Differences from REST:
    - /stream/{machine_id} returns continuous SSE data
    - Must keep connection open
    - One stream per machine
    - Use threading for parallel listening
    
    Pattern:
        data: {"machine_id":"CNC_01","temperature_C":75.5,...}
        data: {"machine_id":"CNC_01","temperature_C":75.6,...}
        data: {"machine_id":"CNC_01","temperature_C":75.7,...}
    """
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        """Initialize SSE stream client"""
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.listening_threads = {}
        self.is_listening = False
        logger.info(f"📡 Stream API Client initialized: {self.base_url}")
    
    def health_check(self) -> bool:
        """Check if API server is running"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=2)
            is_healthy = response.status_code == 200
            status = "✅ API is healthy" if is_healthy else f"❌ API returned {response.status_code}"
            logger.info(status)
            return is_healthy
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
    
    def listen_to_machine(
        self,
        machine_id: str,
        callback: Callable[[Dict], None],
        error_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Listen to SSE stream for ONE machine
        Runs in current thread (call from a thread!)
        
        Args:
            machine_id: Machine ID (e.g., "CNC_01")
            callback: Function(data) called when new data arrives
            error_callback: Function(error_msg) called on error
        """
        try:
            url = f"{self.base_url}/stream/{machine_id}"
            logger.info(f"🎧 Listening to {machine_id} at {url}")
            
            # Keep connection open (stream=True, no timeout)
            response = self.session.get(url, stream=True, timeout=None)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if not self.is_listening:
                    logger.info(f"🛑 Stopped listening to {machine_id}")
                    break
                
                if line:
                    try:
                        # Parse SSE format: "data: {...json...}"
                        if isinstance(line, bytes):
                            line = line.decode('utf-8')
                        
                        if line.startswith('data: '):
                            # Remove "data: " prefix
                            json_str = line[6:]
                        else:
                            # Try parsing directly as JSON
                            json_str = line
                        
                        data = json.loads(json_str)
                        normalized = self._normalize_data(data)
                        callback(normalized)
                        
                    except json.JSONDecodeError as e:
                        logger.debug(f"Invalid JSON from {machine_id}: {line}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing data from {machine_id}: {e}")
                        if error_callback:
                            error_callback(str(e))
                        continue
        
        except requests.exceptions.ConnectionError as e:
            msg = f"Cannot connect to {self.base_url}: {e}"
            logger.error(f"❌ {msg}")
            if error_callback:
                error_callback(msg)
        except requests.exceptions.Timeout as e:
            msg = f"Connection timeout for {machine_id}: {e}"
            logger.error(f"⏱️ {msg}")
            if error_callback:
                error_callback(msg)
        except requests.exceptions.HTTPError as e:
            msg = f"HTTP error {e.response.status_code}: {e.response.reason}"
            logger.error(f"🔴 {msg}")
            if error_callback:
                error_callback(msg)
        except Exception as e:
            msg = f"Stream error for {machine_id}: {e}"
            logger.error(f"⚠️ {msg}")
            if error_callback:
                error_callback(msg)
    
    def listen_all_machines(
        self,
        machine_ids: List[str],
        callback: Callable[[str, Dict], None],
        error_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, threading.Thread]:
        """
        🔥 Listen to ALL machines in PARALLEL using threads
        
        Each machine gets its own thread:
        - CNC_01 → Thread 1
        - CNC_02 → Thread 2
        - PUMP_03 → Thread 3
        - CONVEYOR_04 → Thread 4
        
        All run simultaneously!
        
        Args:
            machine_ids: List of machine IDs to listen to
            callback: Function(machine_id, data) called when data arrives
            error_callback: Function(machine_id, error_msg) on error
            
        Returns:
            Dictionary of {machine_id: thread}
        """
        self.is_listening = True
        logger.info(f"🚀 Starting parallel listeners for {len(machine_ids)} machines")
        
        threads = {}
        
        for machine_id in machine_ids:
            def listen_machine(m_id):
                """Closure to capture machine_id"""
                def data_callback(data):
                    callback(m_id, data)
                
                def error_cb(error_msg):
                    if error_callback:
                        error_callback(m_id, error_msg)
                
                self.listen_to_machine(m_id, data_callback, error_cb)
            
            # Create and start thread
            thread = threading.Thread(
                target=listen_machine,
                args=(machine_id,),
                daemon=True,
                name=f"Stream-{machine_id}"
            )
            thread.start()
            threads[machine_id] = thread
            logger.info(f"✅ Thread started for {machine_id}")
        
        return threads
    
    def stop_listening(self):
        """Stop all listening threads"""
        logger.info("🛑 Stopping all listeners")
        self.is_listening = False
        
        for machine_id, thread in self.listening_threads.items():
            thread.join(timeout=2)
            logger.info(f"✅ Stopped {machine_id}")
        
        self.listening_threads.clear()
    
    def send_alert(
        self,
        machine_id: str,
        alert_type: str,
        message: str,
        data: Dict
    ) -> bool:
        """
        Send alert back to API
        
        Args:
            machine_id: Machine ID
            alert_type: CRITICAL, WARNING, WATCH
            message: Alert message
            data: Sensor data that triggered alert
            
        Returns:
            True if alert sent successfully
        """
        try:
            alert = {
                "machine_id": machine_id,
                "alert_type": alert_type,
                "message": message,
                "reading": data,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            response = self.session.post(
                f"{self.base_url}/alert",
                json=alert,
                timeout=5
            )
            response.raise_for_status()
            
            logger.info(f"📢 Alert sent for {machine_id}: {alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False
    
    def get_historical_data(self, machine_id: str, days: int = 7) -> Optional[List[Dict]]:
        """Get historical data for ML training"""
        try:
            url = f"{self.base_url}/history/{machine_id}"
            response = self.session.get(url, params={"days": days}, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, list):
                return [self._normalize_data(record) for record in data]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {machine_id}: {e}")
            return None
    
    def get_all_machines(self) -> Optional[List[str]]:
        """Get list of all available machines"""
        try:
            response = self.session.get(f"{self.base_url}/machines", timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "machines" in data:
                return data["machines"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get machines list: {e}")
            return None
    
    def _normalize_data(self, data: Dict) -> Dict:
        """
        Normalize API response to standard format
        Handles different response formats from different API servers
        """
        return {
            "machine_id": data.get("machine_id") or data.get("id") or "UNKNOWN",
            "timestamp": data.get("timestamp") or datetime.datetime.now().isoformat(),
            "temperature_C": float(data.get("temperature_C") or data.get("temp") or 0),
            "vibration_mm_s": float(data.get("vibration_mm_s") or data.get("vibration") or 0),
            "rpm": float(data.get("rpm") or data.get("speed") or 0),
            "current_A": float(data.get("current_A") or data.get("current") or 0),
            "status": data.get("status") or "running",
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_listening()
        self.session.close()
