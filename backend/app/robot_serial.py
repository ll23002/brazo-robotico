import serial
import serial.tools.list_ports
import time
import threading
from typing import List, Dict, Optional
from .state import state, SystemStatus
from .config import config

class RobotSerialController:
    def __init__(self):
        self.serial_conn: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self.is_busy = False

    def connect(self, port: Optional[str] = None) -> bool:
        with self._lock:
            target_port = port or config.serial_port
            if self.serial_conn and self.serial_conn.is_open:
                if self.serial_conn.port == target_port:
                    state.is_connected_serial = True
                    return True
                self._disconnect_internal()

            try:
                state.add_log("SERIAL", f"Intentando conectar a {target_port} ({config.baud_rate} baud)...")
                self.serial_conn = serial.Serial(target_port, config.baud_rate, timeout=1)
                time.sleep(2)  # Espera para reset de ESP32/Arduino tras DTR
                self.serial_conn.reset_input_buffer()
                state.is_connected_serial = True
                state.add_log("SERIAL", f"Conexión exitosa con el microcontrolador en {target_port}")
                
                # Leer cualquier saludo inicial del firmware
                time.sleep(0.2)
                while self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        state.add_log("ARDUINO", line)
                return True
            except Exception as e:
                state.is_connected_serial = False
                state.add_log("SERIAL", f"Fallo al conectar puerto {target_port}: {e}")
                self.serial_conn = None
                return False

    def _disconnect_internal(self):
        if self.serial_conn:
            try:
                if self.serial_conn.is_open:
                    self.serial_conn.close()
            except Exception:
                pass
            self.serial_conn = None
        state.is_connected_serial = False

    def disconnect(self):
        with self._lock:
            if self.serial_conn and self.serial_conn.is_open:
                try:
                    # Enviar comando de postura inicial segura antes de desconectar
                    self.serial_conn.write(b"1\n")
                    self.serial_conn.flush()
                except Exception:
                    pass
            self._disconnect_internal()
            state.add_log("SERIAL", "Puerto serial desconectado.")

    def send_raw_command(self, cmd: str) -> Optional[str]:
        """Envía un comando simple y espera respuesta (para calibración / pruebas directas)"""
        with self._lock:
            if not self.serial_conn or not self.serial_conn.is_open:
                state.add_log("SERIAL", f"No se pudo enviar '{cmd}': puerto serial cerrado")
                return None
            try:
                self.serial_conn.reset_input_buffer()
                full_cmd = f"{cmd.strip()}\n"
                self.serial_conn.write(full_cmd.encode())
                self.serial_conn.flush()
                state.add_log("SERIAL", f"Orden enviada: {cmd}")
                
                # Esperar respuesta
                respuestas = []
                start = time.time()
                while time.time() - start < 1.5:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            respuestas.append(line)
                            state.add_log("ARDUINO", line)
                    time.sleep(0.05)
                return "\n".join(respuestas) if respuestas else "Sin respuesta del brazo"
            except Exception as e:
                state.add_log("SERIAL", f"Error enviando comando '{cmd}': {e}")
                return None

    def execute_routine(self, tipo_tornillo: int):
        """Ejecuta la rutina de recolección de tornillo en segundo plano"""
        threading.Thread(target=self._run_routine_thread, args=(tipo_tornillo,), daemon=True).start()

    def _run_routine_thread(self, tipo_tornillo: int):
        if self.is_busy:
            state.add_log("SISTEMA", "Brazo ocupado. Se omite solicitud.")
            return

        self.is_busy = True
        prev_status = state.get_status()
        state.set_status(SystemStatus.BUSY)
        state.add_log("SISTEMA", f"Iniciando recolección de Tornillo Tipo {tipo_tornillo}")

        with self._lock:
            if not self.serial_conn or not self.serial_conn.is_open:
                state.add_log("SERIAL", "No se ejecutó la rutina: sin conexión serial.")
                self.is_busy = False
                state.set_status(prev_status)
                return

            secuencia = ["1", "2", f"4,{tipo_tornillo}", "1"]
            for orden in secuencia:
                try:
                    comando = f"{orden}\n"
                    self.serial_conn.write(comando.encode())
                    self.serial_conn.flush()
                    state.add_log("SERIAL", f"Orden enviada al brazo: {orden}")

                    # Tiempos de espera acordes al firmware
                    if orden in ("2", "5") or orden.startswith("4"):
                        time.sleep(0.7)
                    else:
                        time.sleep(0.5)

                    while self.serial_conn.in_waiting > 0:
                        respuesta = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                        if respuesta:
                            state.add_log("ARDUINO", respuesta)
                except Exception as e:
                    state.add_log("SERIAL", f"Error en secuencia orden '{orden}': {e}")

        state.add_log("SISTEMA", "Rutina completada. Retomando visión.")
        self.is_busy = False
        state.set_status(prev_status if prev_status != SystemStatus.BUSY else SystemStatus.RUNNING)

    @staticmethod
    def list_ports() -> List[Dict[str, str]]:
        ports = serial.tools.list_ports.comports()
        result = []
        for p in ports:
            result.append({
                "device": p.device,
                "description": p.description,
                "hwid": p.hwid,
                "is_usb": ("USB" in p.device or "ACM" in p.device or "USB" in (p.description or ""))
            })
        return result

robot_serial = RobotSerialController()
