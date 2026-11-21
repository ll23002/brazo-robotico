#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="/home/alexander/miniconda3/envs/yolo/bin/python"

echo "=========================================================="
echo "🤖 Iniciando Plataforma Web: Mano Robótica + YOLO AI"
echo "=========================================================="
echo "Directorio del Proyecto: $REPO_DIR"
echo "Entorno Python: $PYTHON_BIN"
echo "----------------------------------------------------------"

# Verificar python de conda
if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ Error: No se encontró el binario de Python en $PYTHON_BIN"
    exit 1
fi

# Función de limpieza al detener
cleanup() {
    local exit_code=$?
    echo ""
    echo "🛑 Deteniendo servidores..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo "✅ Servidores detenidos."
    exit "$exit_code"
}

trap cleanup SIGINT SIGTERM EXIT

echo "1. Iniciando Backend FastAPI en http://127.0.0.1:8000..."
cd "$REPO_DIR/backend"
"$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Esperando a que el backend esté listo..."
BACKEND_READY=0
for attempt in {1..60}; do
    if curl --fail --silent --max-time 1 http://127.0.0.1:8000/api/status >/dev/null; then
        BACKEND_READY=1
        break
    fi

    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "❌ Error: el proceso del backend terminó antes de estar listo."
        exit 1
    fi

    sleep 1
done

if [ "$BACKEND_READY" -ne 1 ]; then
    echo "❌ Error: el backend no respondió en 60 segundos."
    exit 1
fi

echo "2. Iniciando Frontend Vue 3 en http://localhost:5173..."
cd "$REPO_DIR/frontend"
npm run dev -- --host &
FRONTEND_PID=$!

echo ""
echo "🚀 ¡Aplicación lista y corriendo!"
echo "👉 Abre tu navegador en: http://localhost:5173"
echo "👉 API Backend Swagger:   http://localhost:8000/docs"
echo "Presiona Ctrl + C para detener todos los servicios."
echo ""

wait
