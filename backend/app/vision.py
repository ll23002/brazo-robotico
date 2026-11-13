import cv2
import time
import threading
import numpy as np
import os
from typing import Optional
from ultralytics import YOLO
from .config import config
from .state import state, SystemStatus
from .robot_serial import robot_serial

class VisionManager:
    def __init__(self):
        self.model: Optional[YOLO] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Último frame codificado en JPEG listo para streaming MJPEG
        self.latest_jpeg: Optional[bytes] = None
        
        # Variables de control temporal de detección
        self.tiempo_primera_deteccion = 0.0
        self.objeto_en_pantalla = False
        self.objeto_clase_actual = -1
        
        self.load_model()

    def load_model(self):
        try:
            if os.path.exists(config.model_path):
                state.add_log("YOLO", f"Cargando modelo desde {config.model_path}...")
                self.model = YOLO(config.model_path)
                state.add_log("YOLO", "Modelo cargado exitosamente.")
            else:
                state.add_log("YOLO", f"ADVERTENCIA: Archivo de modelo no encontrado en {config.model_path}")
                self.model = None
        except Exception as e:
            state.add_log("YOLO", f"Error cargando modelo YOLO: {e}")
            self.model = None

    def start_vision(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()

    def stop_vision(self):
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._release_camera()

    def _init_camera(self, cam_id: int) -> bool:
        self._release_camera()
        try:
            state.add_log("CÁMARA", f"Iniciando captura de video en índice {cam_id}...")
            cap = cv2.VideoCapture(cam_id)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.frame_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.frame_height)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    self.cap = cap
                    state.is_camera_active = True
                    state.add_log("CÁMARA", f"Cámara {cam_id} conectada y activa.")
                    return True
            cap.release()
        except Exception as e:
            state.add_log("CÁMARA", f"Error iniciando cámara {cam_id}: {e}")
        
        self.cap = None
        state.is_camera_active = False
        return False

    def _release_camera(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        state.is_camera_active = False

    def change_camera(self, new_id: int):
        with self._lock:
            config.camera_id = new_id
            config.save()
            self._init_camera(new_id)

    def _generate_placeholder(self, title: str, subtitle: str) -> np.ndarray:
        img = np.zeros((config.frame_height, config.frame_width, 3), dtype=np.uint8)
        # Fondo degradado o grid tenue
        img[:] = (25, 27, 34)
        cv2.putText(img, title, (50, config.frame_height // 2 - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2, cv2.LINE_AA)
        cv2.putText(img, subtitle, (50, config.frame_height // 2 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1, cv2.LINE_AA)
        return img

    def _capture_loop(self):
        self._init_camera(config.camera_id)
        last_frame_time = time.time()
        
        while self._running:
            current_status = state.get_status()
            
            if not self.cap or not self.cap.isOpened():
                frame = self._generate_placeholder(
                    "Cámara no disponible", 
                    f"Índice actual: {config.camera_id}. Revisa la configuración o prueba con 0, 1 o 2."
                )
                time.sleep(0.3)
            else:
                ret, frame = self.cap.read()
                if not ret:
                    frame = self._generate_placeholder("Error de lectura de video", "Reconectando cámara...")
                    time.sleep(0.2)
                    self._init_camera(config.camera_id)
                else:
                    # Cálculo de FPS
                    now = time.time()
                    dt = now - last_frame_time
                    last_frame_time = now
                    if dt > 0:
                        state.fps = 0.9 * state.fps + 0.1 * (1.0 / dt)

                    # Procesamiento según estado
                    if current_status == SystemStatus.RUNNING and not robot_serial.is_busy:
                        frame = self._process_yolo_detection(frame)
                    elif robot_serial.is_busy:
                        self._draw_overlay_banner(frame, "BRAZO EN MOVIMIENTO...", (0, 140, 255))
                    elif current_status == SystemStatus.PAUSED:
                        self._draw_overlay_banner(frame, "DETECCIÓN PAUSADA", (0, 215, 255))
                    elif current_status == SystemStatus.STOPPED:
                        self._draw_overlay_banner(frame, "SISTEMA EN ESPERA (APAGADO)", (80, 80, 200))

            # Codificar a JPEG
            try:
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    self.latest_jpeg = buffer.tobytes()
            except Exception as e:
                pass

            time.sleep(0.015)  # Limitar a ~30-45 FPS para optimizar CPU

    def _draw_overlay_banner(self, frame: np.ndarray, text: str, color: tuple):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, 20), (w - 20, 80), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.putText(frame, text, (40, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)

    def _process_yolo_detection(self, frame: np.ndarray) -> np.ndarray:
        if self.model is None:
            cv2.putText(frame, "Modelo YOLO no cargado", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            return frame

        try:
            resultados = self.model(frame, stream=True, verbose=False, conf=config.confidence)
            deteccion_en_este_frame = False

            for r in resultados:
                frame = r.plot()

                if len(r.boxes) > 0:
                    deteccion_en_este_frame = True
                    clase_id = int(r.boxes.cls[0].item())
                    state.detected_class_id = clase_id
                    state.last_detected_object = f"Tornillo Tipo {clase_id + 1}"

                    if not self.objeto_en_pantalla or self.objeto_clase_actual != clase_id:
                        self.tiempo_primera_deteccion = time.time()
                        self.objeto_en_pantalla = True
                        self.objeto_clase_actual = clase_id
                        state.persistence_progress = 0.0
                        state.add_log("YOLO", f"Posible Tornillo Tipo {clase_id + 1} detectado... validando persistencia.")
                    else:
                        tiempo_transcurrido = time.time() - self.tiempo_primera_deteccion
                        progress = min(1.0, tiempo_transcurrido / max(0.01, config.recognition_time))
                        state.persistence_progress = progress

                        # Dibujar barra visual de validación en la esquina inferior
                        self._draw_persistence_bar(frame, progress, tiempo_transcurrido, config.recognition_time)

                        if tiempo_transcurrido >= config.recognition_time:
                            state.add_log("YOLO", f"¡Validado por {config.recognition_time:.2f}s! Disparando rutina para Tipo {clase_id + 1}")
                            self.objeto_en_pantalla = False
                            state.persistence_progress = 0.0

                            # Iniciar rutina física con el brazo
                            if clase_id in (0, 1):
                                robot_serial.execute_routine(clase_id + 1)
                            else:
                                robot_serial.execute_routine(1)

            if not deteccion_en_este_frame:
                self.objeto_en_pantalla = False
                self.objeto_clase_actual = -1
                self.tiempo_primera_deteccion = 0.0
                state.persistence_progress = 0.0
                state.last_detected_object = "Ninguno"
                state.detected_class_id = -1

        except Exception as e:
            state.add_log("YOLO", f"Error en inferencia: {e}")

        return frame

    def _draw_persistence_bar(self, frame: np.ndarray, progress: float, actual: float, total: float):
        h, w = frame.shape[:2]
        bar_x = 40
        bar_y = h - 60
        bar_w = w - 80
        bar_h = 24

        # Fondo de la barra
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (30, 30, 30), -1)
        # Relleno del progreso (Verde a Cyan)
        fill_w = int(bar_w * progress)
        color = (0, 255, int(255 * progress))
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), color, -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (200, 200, 200), 1)

        # Texto informativo
        info_text = f"Validando persistencia: {actual:.2f}s / {total:.2f}s ({int(progress * 100)}%)"
        cv2.putText(frame, info_text, (bar_x + 10, bar_y + 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

vision_manager = VisionManager()
