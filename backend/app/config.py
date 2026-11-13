import os
import json
from pydantic import BaseModel

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
DEFAULT_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "best.pt"))

class AppConfig(BaseModel):
    camera_id: int = 2
    serial_port: str = "/dev/ttyUSB0"
    baud_rate: int = 115200
    recognition_time: float = 0.2  # TIEMPO_REQUERIDO en segundos
    confidence: float = 0.6
    model_path: str = DEFAULT_MODEL_PATH
    frame_width: int = 640
    frame_height: int = 480

    @classmethod
    def load(cls) -> "AppConfig":
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls(**data)
            except Exception as e:
                print(f"[CONFIG] Error cargando config.json, usando defaults: {e}")
        cfg = cls()
        cfg.save()
        return cfg

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.model_dump(), f, indent=2)
        except Exception as e:
            print(f"[CONFIG] Error guardando config.json: {e}")

config = AppConfig.load()
