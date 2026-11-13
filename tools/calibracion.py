import serial
import time

# --- CONFIGURACIÓN SERIAL ---
puerto_esp32 = '/dev/ttyUSB0'  # Puerto configurado para Linux
try:
    arduino = serial.Serial(puerto_esp32, 115200, timeout=1)
    time.sleep(2)
    arduino.reset_input_buffer()
    print("Conexión serial establecida con el brazo.")
except Exception as e:
    print(f"Error abriendo puerto serial: {e}")
    arduino = None

if arduino:
    print("\n=======================================================")
    print("🤖 MODO DE CALIBRACIÓN MANUAL ACTIVO")
    print("Envía los pasos individualmente acordes a tu Arduino:")
    print("  1   -> Ir a posición inicial (Centro, abierta)")
    print("  2   -> Bajar a agarrar (Garra 45° con delay)")
    print("  4,1 -> Rotar base a derecha extrema (0°)")
    print("  4,2 -> Rotar base a izquierda extrema (180°)")
    print("  q   -> Salir del programa")
    print("=======================================================\n")

    while True:
        entrada = input("Ingresa comando: ").strip().lower()
        
        if entrada == 'q':
            print("Saliendo del modo de calibración...")
            break
            
        elif entrada != '':
            # 1. Limpiamos cualquier mensaje viejo atascado en el cable
            arduino.reset_input_buffer()
            
            # 2. Enviamos el comando exacto con el salto de línea que espera readStringUntil('\n')
            comando_directo = f"{entrada}\n"
            arduino.write(comando_directo.encode())
            arduino.flush()
            print(f"Enviando orden manual: {entrada}")
            
            # 3. Esperamos activamente las respuestas dando tiempo a los delay() del Arduino
            # El caso 5 tiene delay de 1.5s, por lo que esperamos hasta 2 segundos por respuestas.
            tiempo_inicio = time.time()
            while time.time() - tiempo_inicio < 2.0:
                if arduino.in_waiting > 0:
                    respuesta = arduino.readline().decode('utf-8', errors='ignore').strip()
                    if respuesta:
                        print(f"ESP32 Responde: {respuesta}")

    arduino.close()