from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import cv2
import time
from typing import Optional, Dict, Any

from .config import config, AppConfig
from .state import state, SystemStatus
from .robot_serial import robot_serial
from .vision import vision_manager
from .arduino_cli import arduino_cli_mgr

app = FastAPI(title="Mano Robótica YOLO Web API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    state.add_log("SISTEMA", "Iniciando servidor de control para mano robótica...")
    # Iniciar motor de visión en segundo plano
    vision_manager.start_vision()

@app.on_event("shutdown")
def shutdown_event():
    state.add_log("SISTEMA", "Apagando servidor...")
    vision_manager.stop_vision()
    robot_serial.disconnect()

@app.get("/api/status")
def get_status():
    return state.get_snapshot()

@app.get("/api/config")
def get_config():
    return config.model_dump()

class ConfigUpdateRequest(BaseModel):
    camera_id: Optional[int] = None
    serial_port: Optional[str] = None
    baud_rate: Optional[int] = None
    recognition_time: Optional[float] = None
    confidence: Optional[float] = None

@app.put("/api/config")
def update_config(update: ConfigUpdateRequest):
    changed_cam = False
    changed_port = False

    if update.camera_id is not None and update.camera_id != config.camera_id:
        config.camera_id = update.camera_id
        changed_cam = True

    if update.serial_port is not None and update.serial_port != config.serial_port:
        config.serial_port = update.serial_port
        changed_port = True

    if update.baud_rate is not None:
        config.baud_rate = update.baud_rate

    if update.recognition_time is not None:
        config.recognition_time = max(0.05, update.recognition_time)

    if update.confidence is not None:
        config.confidence = min(1.0, max(0.1, update.confidence))

    config.save()
    state.add_log("CONFIG", f"Configuración actualizada: Tiempo rec={config.recognition_time}s, Cam={config.camera_id}, Puerto={config.serial_port}")

    if changed_cam:
        vision_manager.change_camera(config.camera_id)

    if changed_port and state.is_connected_serial:
        robot_serial.connect(config.serial_port)

    return {"success": True, "config": config.model_dump()}

@app.post("/api/control/{action}")
def control_system(action: str):
    action = action.lower()
    if action == "start":
        # Conectar serial si no está conectado
        if not state.is_connected_serial:
            robot_serial.connect(config.serial_port)
        state.set_status(SystemStatus.RUNNING)
        return {"success": True, "status": state.get_status().value}

    elif action == "pause":
        state.set_status(SystemStatus.PAUSED)
        return {"success": True, "status": state.get_status().value}

    elif action == "stop":
        state.set_status(SystemStatus.STOPPED)
        robot_serial.disconnect()
        return {"success": True, "status": state.get_status().value}

    else:
        raise HTTPException(status_code=400, detail=f"Acción '{action}' no válida. Usa start, pause o stop.")

def mjpeg_frame_generator():
    while True:
        frame = vision_manager.latest_jpeg
        if frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        time.sleep(0.033)  # ~30 FPS

@app.get("/api/video/stream")
def video_stream():
    return StreamingResponse(
        mjpeg_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/system/ports")
def get_ports():
    ports = robot_serial.list_ports()
    return {
        "ports": ports,
        "current_configured": config.serial_port,
        "is_connected": state.is_connected_serial,
        "host_guide": {
            "commands": [
                {"name": "Ver dispositivos USB/ACM conectados", "cmd": "ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null"},
                {"name": "Ver logs del kernel al conectar el USB", "cmd": "dmesg | grep -E 'ttyUSB|ttyACM|ch341|cp210x|ftdi'"},
                {"name": "Permisos de usuario para puerto serial", "cmd": "sudo usermod -a -G dialout $USER"}
            ],
            "tip": "Si no aparece /dev/ttyUSB0, desconecta y reconecta el cable USB del ESP32/Arduino y ejecuta 'dmesg | tail -n 20' para ver el nombre asignado."
        }
    }

@app.get("/api/system/cameras")
def get_available_cameras():
    """Detecta qué índices de cámara responden en OpenCV"""
    available = []
    for idx in range(4):
        # Si es la cámara actualmente abierta por el manager, sabemos que está disponible
        if idx == config.camera_id and vision_manager.cap and vision_manager.cap.isOpened():
            available.append({"id": idx, "name": f"Cámara {idx} (En uso actual)", "active": True})
            continue

        temp_cap = cv2.VideoCapture(idx)
        if temp_cap.isOpened():
            ret, _ = temp_cap.read()
            if ret:
                available.append({"id": idx, "name": f"Cámara {idx}", "active": False})
            temp_cap.release()
    return {"cameras": available}

@app.get("/api/logs")
def get_logs():
    return {"logs": state.get_logs(100)}

class FlashRequest(BaseModel):
    fqbn: Optional[str] = "esp32:esp32:esp32"
    port: Optional[str] = None

@app.get("/api/arduino/boards")
def get_arduino_boards():
    return {"boards": arduino_cli_mgr.get_available_boards()}

@app.post("/api/arduino/flash")
def flash_arduino(req: FlashRequest):
    # Si el puerto serial está en uso por la app, desconectarlo temporalmente para liberar el puerto
    was_connected = state.is_connected_serial
    if was_connected:
        robot_serial.disconnect()

    target_port = req.port or config.serial_port
    target_fqbn = req.fqbn or "esp32:esp32:esp32"

    result = arduino_cli_mgr.compile_and_upload(target_fqbn, target_port)

    # Si estaba conectado antes, intentar reconectar
    if was_connected:
        time.sleep(2)
        robot_serial.connect(target_port)

    return result

class ManualCommandRequest(BaseModel):
    command: str

@app.post("/api/robot/command")
def manual_command(req: ManualCommandRequest):
    if not state.is_connected_serial:
        raise HTTPException(status_code=400, detail="Puerto serial no está conectado")
    resp = robot_serial.send_raw_command(req.command)
    return {"command": req.command, "response": resp}
