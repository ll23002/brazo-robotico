#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// --- PINES DE LOS MOTORES ---
#define MOTOR_BASE 0
const int PIN_B1 = 1;
const int PIN_B2 = 2;
const int PIN_GARRA = 3;

// --- CONSTANTES DE LOS SERVOS POSICIONALES ---
const int SERVOMIN = 150; 
const int SERVOMAX = 600; 

// Cambia a 270 si adquiriste la versión de 270 grados
const int ANGULO_MAX_BASE = 270; 

void setup() {
  Serial.begin(115200);
  
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(10);
  
  // Posición inicial: Asumimos 90 grados como el centro frontal absoluto
  moverBase(90);
  moverServo(PIN_B1, 90);
  moverServo(PIN_B2, 120);
  moverServo(PIN_GARRA, 90);
  
  Serial.println("Cerebro Motriz Posicional Listo. Esperando ordenes de YOLO...");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input.length() == 0) return;

    int orden = 0;
    int sub_orden = 0;
    
    // Detectar si hay una coma para las órdenes dobles (como 4,1 o 4,2)
    int commaIndex = input.indexOf(',');
    if (commaIndex > 0) {
      orden = input.substring(0, commaIndex).toInt();
      sub_orden = input.substring(commaIndex + 1).toInt();
    } else {
      orden = input.toInt();
    }

    switch(orden) {
      case 1:
        moverBase(90); // Centro
        moverServo(PIN_B1, 90);
        delay(500);
        moverServo(PIN_B2, 120);
        moverServo(PIN_GARRA, 90);
        delay(500);
        break;

      case 2:
        moverBase(90); // Mantiene el centro
        moverServo(PIN_B2, 140);
        delay(500);
        moverServo(PIN_B1, 130);

        delay(500); 
        moverServo(PIN_GARRA, 40); 
        delay(500);
        break;

      case 3:
        moverBase(180); // Mantiene el centro
        delay(500);
        moverServo(PIN_B1, 180);
        moverServo(PIN_B2, 125);
        moverServo(PIN_GARRA, 45);
        delay(500);
        break;

      case 4:
        // Se reemplazan los valores relativos (-90) por coordenadas absolutas
        if (sub_orden == 1) {
          moverBase(0); // Gira a la derecha extrema
          delay(1000);
          moverServo(PIN_GARRA, 90);
        } else if (sub_orden == 2) {
          moverBase(180); // Gira a la izquierda extrema
          delay(1000);
          moverServo(PIN_GARRA, 90);
        }
        moverServo(PIN_B1, 180);
        moverServo(PIN_B2, 125);
        delay(500);
        break;

      case 5:
        // No movemos la base, se queda en el lado donde la dejó el paso 4
        moverServo(PIN_B1, 130);
        moverServo(PIN_B2, 115);
        delay(1500); 
        moverServo(PIN_GARRA, 90); 
        delay(500);
        break;
        
      default:
        Serial.println("❌ Orden no reconocida.");
        return; // Sale del loop si la orden no es válida para no imprimir confirmación falsa
    }
    
    // Confirmación visual en el Monitor Serie de que las órdenes pasaron al PCA9685
    Serial.print("✅ Orden recibida: ");
    Serial.print(input);
    Serial.println(" -> Señales PWM enviadas al PCA9685 y motores actualizados.");
  }
}

// Función dedicada para la base posicional
void moverBase(int angulo) {
  angulo = constrain(angulo, 0, ANGULO_MAX_BASE); 
  int pulso = map(angulo, 0, ANGULO_MAX_BASE, SERVOMIN, SERVOMAX);
  pwm.setPWM(MOTOR_BASE, 0, pulso);
}

// Función para las articulaciones
void moverServo(int pin, int angulo) {
  angulo = constrain(angulo, 0, 180); 
  int pulso = map(angulo, 0, 180, SERVOMIN, SERVOMAX);
  pwm.setPWM(pin, 0, pulso);
}