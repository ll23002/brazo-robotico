import threading
import time
from collections import deque
from enum import Enum
from typing import List, Dict, Any

class SystemStatus(str, Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    BUSY = "BUSY"

class LogEntry:
    def __init__(self, source: str, message: str):
        self.timestamp = time.strftime("%H:%M:%S")
        self.source = source
        self.message = message

    def to_dict(self) -> Dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "message": self.message
        }

class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        self.status: SystemStatus = SystemStatus.STOPPED
        self.is_connected_serial: bool = False
        self.is_camera_active: bool = False
        self.last_detected_object: str = "Ninguno"
        self.detected_class_id: int = -1
        self.persistence_progress: float = 0.0  # 0.0 a 1.0
        self.fps: float = 0.0
        self.logs: deque = deque(maxlen=200)

    def set_status(self, new_status: SystemStatus):
        with self._lock:
            self.status = new_status
        self.add_log("SISTEMA", f"Estado cambiado a {new_status.value}")

    def get_status(self) -> SystemStatus:
        with self._lock:
            return self.status

    def add_log(self, source: str, message: str):
        with self._lock:
            self.logs.append(LogEntry(source, message).to_dict())

    def get_logs(self, limit: int = 100) -> List[Dict[str, str]]:
        with self._lock:
            return list(self.logs)[-limit:]

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self.status.value,
                "is_connected_serial": self.is_connected_serial,
                "is_camera_active": self.is_camera_active,
                "last_detected_object": self.last_detected_object,
                "detected_class_id": self.detected_class_id,
                "persistence_progress": round(self.persistence_progress, 2),
                "fps": round(self.fps, 1)
            }

state = AppState()
