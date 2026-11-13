import subprocess
import os
from typing import Dict, Any, List
from .state import state

ARDUINO_CLI_BIN = "/usr/bin/arduino-cli"
SKETCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "arduino-final"))

AVAILABLE_BOARDS = [
    {"name": "ESP32 Dev Module (Recomendado)", "fqbn": "esp32:esp32:esp32"},
    {"name": "Arduino Uno", "fqbn": "arduino:avr:uno"},
    {"name": "Arduino Nano", "fqbn": "arduino:avr:nano"},
    {"name": "Arduino Mega 2560", "fqbn": "arduino:avr:mega"}
]

class ArduinoCliManager:
    @staticmethod
    def get_available_boards() -> List[Dict[str, str]]:
        return AVAILABLE_BOARDS

    @staticmethod
    def check_cli_installed() -> bool:
        return os.path.exists(ARDUINO_CLI_BIN)

    @staticmethod
    def compile_sketch(fqbn: str) -> Dict[str, Any]:
        if not ArduinoCliManager.check_cli_installed():
            return {"success": False, "message": "arduino-cli no está instalado en el sistema"}

        state.add_log("ARDUINO-CLI", f"Iniciando compilación para placa {fqbn}...")
        cmd = [ARDUINO_CLI_BIN, "compile", "--fqbn", fqbn, SKETCH_DIR]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                state.add_log("ARDUINO-CLI", "Compilación exitosa.")
                return {"success": True, "output": res.stdout}
            else:
                state.add_log("ARDUINO-CLI", f"Error en compilación: {res.stderr}")
                return {"success": False, "output": res.stdout, "error": res.stderr}
        except Exception as e:
            state.add_log("ARDUINO-CLI", f"Excepción durante la compilación: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def upload_sketch(fqbn: str, port: str) -> Dict[str, Any]:
        if not ArduinoCliManager.check_cli_installed():
            return {"success": False, "message": "arduino-cli no está instalado en el sistema"}

        state.add_log("ARDUINO-CLI", f"Subiendo firmware a {port} ({fqbn})...")
        cmd = [ARDUINO_CLI_BIN, "upload", "-p", port, "--fqbn", fqbn, SKETCH_DIR]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                state.add_log("ARDUINO-CLI", "Firmware subido exitosamente a la placa.")
                return {"success": True, "output": res.stdout}
            else:
                state.add_log("ARDUINO-CLI", f"Fallo al subir firmware: {res.stderr}")
                return {"success": False, "output": res.stdout, "error": res.stderr}
        except Exception as e:
            state.add_log("ARDUINO-CLI", f"Excepción durante subida de firmware: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def compile_and_upload(fqbn: str, port: str) -> Dict[str, Any]:
        comp_res = ArduinoCliManager.compile_sketch(fqbn)
        if not comp_res["success"]:
            return comp_res
        return ArduinoCliManager.upload_sketch(fqbn, port)

arduino_cli_mgr = ArduinoCliManager()
