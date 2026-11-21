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
        self._camera_lock = threading.RLock()
        self._frame_lock = threading.Lock()
        self._jpeg_cond = threading.Condition()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._reader_thread: Optional[threading.Thread] = None

        # Último frame crudo leído por el hilo dedicado de cámara
        self._raw_frame: Optional[np.ndarray] = None
        self._raw_frame_id: int = 0
        self._read_failures: int = 0
        
        # Último frame codificado en JPEG listo para streaming MJPEG
        self.latest_jpeg: Optional[bytes] = None
        self.latest_frame_id: int = 0
        
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
            self._reader_thread = threading.Thread(target=self._camera_reader_loop, daemon=True)
            self._reader_thread.start()
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()

    def stop_vision(self):
        with self._lock:
            self._running = False
        with self._jpeg_cond:
            self._jpeg_cond.notify_all()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._release_camera()

    def _init_camera(self, cam_id: int) -> bool:
        with self._camera_lock:
            self._release_camera()
            try:
                state.add_log("CÁMARA", f"Iniciando captura de video en índice {cam_id}...")
                cap = cv2.VideoCapture(cam_id)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.frame_width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.frame_height)
                if cap.isOpened():
                    ret, first_frame = cap.read()
                    if ret:
                        self.cap = cap
                        with self._frame_lock:
                            self._raw_frame = first_frame
                            self._raw_frame_id += 1
                            self._read_failures = 0
                        state.is_camera_active = True
                        state.add_log("CÁMARA", f"Cámara {cam_id} conectada y activa.")
                        return True
                    state.add_log("CÁMARA", f"No se pudo leer video de la cámara {cam_id}.")
                else:
                    state.add_log("CÁMARA", f"No se pudo abrir la cámara {cam_id} (/dev/video{cam_id}).")
                cap.release()
            except Exception as e:
                state.add_log("CÁMARA", f"Error iniciando cámara {cam_id}: {e}")

            self.cap = None
            state.is_camera_active = False
            return False

    def _release_camera(self):
        with self._camera_lock:
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

    def _camera_reader_loop(self):
        """Hilo dedicado para vaciar el buffer de la cámara y conservar siempre el frame más reciente."""
        while self._running:
            with self._camera_lock:
                cap = self.cap
                camera_open = cap is not None and cap.isOpened()
                if camera_open:
                    ret, frame = cap.read()
                else:
                    ret, frame = False, None

            if not camera_open:
                time.sleep(0.1)
                continue

            if ret and frame is not None:
                with self._frame_lock:
                    self._raw_frame = frame
                    self._raw_frame_id += 1
                    self._read_failures = 0
            else:
                with self._frame_lock:
                    self._read_failures += 1
                time.sleep(0.01)

    def _get_latest_raw_frame(self):
        with self._frame_lock:
            if self._raw_frame is None:
                return False, None, self._read_failures
            return True, self._raw_frame.copy(), self._read_failures

    def wait_for_frame(self, last_frame_id: int, timeout: float = 1.0):
        """Espera hasta que haya un nuevo frame JPEG disponible o venza el timeout."""
        with self._jpeg_cond:
            if self.latest_frame_id == last_frame_id and self._running:
                self._jpeg_cond.wait(timeout=timeout)
            return self.latest_jpeg, self.latest_frame_id

    def _capture_loop(self):
        self._init_camera(config.camera_id)
        last_frame_time = time.time()
        target_interval = 1.0 / 30.0
        
        while self._running:
            loop_start = time.monotonic()
            current_status = state.get_status()

            with self._camera_lock:
                camera_open = self.cap is not None and self.cap.isOpened()

            ret, frame, failures = self._get_latest_raw_frame()

            if not camera_open:
                frame = self._generate_placeholder(
                    "Cámara no disponible", 
                    f"Índice actual: {config.camera_id}. Revisa la configuración o prueba con 0, 1 o 2."
                )
                time.sleep(0.3)
            elif failures >= 15:
                frame = self._generate_placeholder("Error de lectura de video", "Reconectando cámara...")
                time.sleep(0.2)
                self._init_camera(config.camera_id)
            elif not ret or frame is None:
                time.sleep(0.01)
                continue
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

            # Codificar a JPEG y notificar al generador MJPEG
            try:
                ok, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if ok:
                    with self._jpeg_cond:
                        self.latest_jpeg = buffer.tobytes()
                        self.latest_frame_id += 1
                        self._jpeg_cond.notify_all()
            except Exception:
                pass

            elapsed = time.monotonic() - loop_start
            remaining = target_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)

    def _draw_overlay_banner(self, frame: np.ndarray, text: str, color: tuple):
        h, w = frame.shape[:2]
        y1, y2 = 20, min(80, h)
        x1, x2 = 20, max(21, w - 20)
        roi = frame[y1:y2, x1:x2]
        dark = np.full_like(roi, 20)
        cv2.addWeighted(dark, 0.6, roi, 0.4, 0, roi)
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
