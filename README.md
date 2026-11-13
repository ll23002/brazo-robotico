# 🦾 Control de Mano Robótica con YOLO AI y Arduino (Web Platform)

Sistema unificado para el control visual y cinemático de una mano/brazo robótico utilizando inteligencia artificial (Ultralytics YOLO) y microcontrolador (ESP32 / Arduino con PCA9685).

---

## 📁 Estructura del Repositorio

```text
brazo-robotico-web/
├── backend/                  # Servidor FastAPI (Python en entorno Conda 'yolo')
│   ├── app/
│   │   ├── main.py           # Endpoints REST y stream de video MJPEG
│   │   ├── vision.py         # Inferencia YOLO, cálculo de persistencia y OpenCV
│   │   ├── robot_serial.py   # Control serie, rutinas cinemáticas y lectura
│   │   ├── arduino_cli.py    # Integración con arduino-cli sin IDE
│   │   ├── config.py         # Persistencia de configuración
│   │   └── state.py          # Estados del sistema y logs en tiempo real
│   ├── config.json           # Configuración actual guardada
│   └── requirements.txt      # Dependencias pip
├── frontend/                 # Aplicación SPA en Vue 3 + Vite
│   ├── src/
│   │   ├── components/       # Componentes modulares (Video, Controles, Arduino, Logs)
│   │   ├── App.vue           # Vista principal interactiva
│   │   └── style.css         # Estilos oscuros y modernos
│   └── package.json
├── firmware/                 # Código fuente para microcontrolador
│   ├── arduino-final/
│   │   └── arduino-final.ino # Sketch Arduino con librería Adafruit PWM Servo Driver
│   └── flash.sh              # Script para compilar y flashear por consola sin IDE
├── models/
│   └── best.pt               # Pesos entrenados de YOLO para clasificación de tornillos
├── tools/
│   └── calibracion.py        # Herramienta de calibración por comandos en terminal
├── run.sh                    # Lanzador automático de Backend + Frontend
└── README.md
```

---

## 🚀 Inicio Rápido

Para arrancar tanto el backend como la interfaz web en un solo paso:

```bash
cd /home/alexander/brazo-robotico-web
./run.sh
```

Abre tu navegador en:
- **Interfaz Web**: [http://localhost:5173](http://localhost:5173)
- **Documentación API (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🎛️ Funcionalidades de la Interfaz Web

1. **Botones de Control de Estados**:
   - **Iniciar**: Activa la inferencia YOLO y la sincronización con el brazo robótico.
   - **Pausar**: Mantiene el stream de video de la cámara pero detiene temporalmente la detección y los movimientos.
   - **Apagar**: Envía la orden de seguridad (postura inicial "1") al brazo, cierra el puerto serie y libera la cámara.
2. **Stream de Video en Vivo**:
   - Se muestra directamente dentro del navegador mediante flujo MJPEG con las cajas delimitadoras de YOLO y la barra de validación de persistencia temporal.
3. **Parámetros Editables en Tiempo Real**:
   - **Tiempo de Reconocimiento (`TIEMPO_REQUERIDO`)**: Define cuántos segundos continuos debe ser visible el tornillo para ordenar el movimiento. Modificable al instante mediante un control deslizante o numérico.
   - **ID de la Cámara**: Permite cambiar entre el dispositivo `0`, `1`, `2`... sin reiniciar el backend.
   - **Puerto Serial**: Campo editable con valor por defecto `/dev/ttyUSB0` y botón para escanear puertos activos.
4. **Guía de Puertos en Linux**:
   - Modal interactivo con los comandos necesarios para consultar el puerto en la máquina anfitrión (`ls /dev/tty*`, `dmesg`, `dialout`).
5. **Flasheo de Firmware sin IDE de Arduino**:
   - Botón directo en la web para compilar y subir el sketch usando `arduino-cli`.
   - También disponible por terminal mediante `./firmware/flash.sh [/dev/ttyUSB0] [esp32:esp32:esp32]`.

---

## 🔌 Identificación del Puerto Serial en Linux

Si necesitas verificar qué puerto se asignó a tu placa al conectarla por USB:

```bash
# 1. Ver dispositivos USB / ACM disponibles
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null

# 2. Ver mensajes del kernel al enchufar el cable
dmesg | grep -E "ttyUSB|ttyACM|ch341|cp210x|ftdi" | tail -n 10

# 3. Conceder permisos de acceso si aparece "Permission Denied"
sudo usermod -a -G dialout $USER
# (luego reiniciar sesión o ejecutar newgrp dialout)
```
