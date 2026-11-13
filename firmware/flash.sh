#!/usr/bin/env bash
set -e

PORT="${1:-/dev/ttyUSB0}"
FQBN="${2:-esp32:esp32:esp32}"
SKETCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/arduino-final" && pwd)"

echo "=============================================="
echo "🤖 Flasheador de Firmware para Mano Robótica"
echo "=============================================="
echo "Puerto: $PORT"
echo "Placa (FQBN): $FQBN"
echo "Sketch: $SKETCH_DIR"
echo "----------------------------------------------"

if ! command -v arduino-cli &> /dev/null; then
    echo "❌ Error: arduino-cli no está en el PATH."
    exit 1
fi

echo "1. Compilando sketch..."
arduino-cli compile --fqbn "$FQBN" "$SKETCH_DIR"

echo "2. Subiendo a la placa en $PORT..."
arduino-cli upload -p "$PORT" --fqbn "$FQBN" "$SKETCH_DIR"

echo "✅ ¡Firmware subido exitosamente!"
