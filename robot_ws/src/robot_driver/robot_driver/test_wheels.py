#!/usr/bin/env python3
"""
Script simple de prueba para verificar el funcionamiento de las ruedas y servos.
Permite controlar los motores directamente usando la biblioteca Adafruit PCA9685,
sin necesidad de ROS 2, para descartar fallos de hardware o configuración.
"""

import sys
import time

try:
    import board
    import busio
    from adafruit_pca9685 import PCA9685
    from adafruit_motor import servo
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False

# Canales por defecto del HAT PCA9685
MOTOR_LEFT_CHANNEL = 7
MOTOR_RIGHT_CHANNEL = 8

# Configuración de inversión (ajusta según el montaje físico)
INVERT_LEFT = False  
INVERT_RIGHT = True

# Ajuste fino del punto muerto (trim) si la rueda gira sola al estar parada
TRIM_LEFT = 0.0  # Establecido a 0.0 ya que la parada por hardware (duty_cycle = 0) lo hace innecesario
TRIM_RIGHT = 0.0

# Factor de boost para el servo izquierdo al avanzar (sentido positivo)
# El servo izq es físicamente más lento en sentido positivo. Sube este valor (ej. 1.3, 1.5, 1.8)
# hasta que ambas ruedas avancen a la misma velocidad. Máximo útil: 2.0 (ya que se clampea a 1.0)
BOOST_LEFT_FORWARD = 1.5


def print_menu():
    print("\n" + "=" * 50)
    print("      PRUEBA DE RUEDAS / SERVOS DE ROTACIÓN CONTINUA")
    print("=" * 50)
    print(" [W] - Avanzar")
    print(" [S] - Retroceder")
    print(" [A] - Girar a la izquierda (sobre su eje)")
    print(" [D] - Girar a la derecha (sobre su eje)")
    print(" [Space/X] - DETENER MOTORES (Apaga señal PWM a bajo nivel)")
    print(" [Q] - Salir de la prueba")
    print("-" * 50)
    print(" [C] - Calibración/Prueba de punto muerto (Zero-Throttle Test)")
    print("=" * 50)
    print("Introduce un comando y pulsa Enter: ", end="")


def main():
    if not HARDWARE_AVAILABLE:
        print("\n❌ ERROR: No se detectan las librerías necesarias de Adafruit.")
        print("Asegúrate de instalar los requerimientos con:")
        print("  pip3 install adafruit-circuitpython-pca9685 adafruit-circuitpython-motor")
        sys.exit(1)

    print("\n🔍 Inicializando bus I2C y PCA9685...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pca = PCA9685(i2c)
        pca.frequency = 50  # 50 Hz estándar para servos
        
        # Inicializar servos de rotación continua
        servo_left = servo.ContinuousServo(pca.channels[MOTOR_LEFT_CHANNEL])
        servo_right = servo.ContinuousServo(pca.channels[MOTOR_RIGHT_CHANNEL])
        
        # Parar de inmediato apagando los canales a bajo nivel
        pca.channels[MOTOR_LEFT_CHANNEL].duty_cycle = 0
        pca.channels[MOTOR_RIGHT_CHANNEL].duty_cycle = 0
        
        print("✅ Hardware inicializado con éxito.")
        print(f"   - Servo Izquierdo en Canal: {MOTOR_LEFT_CHANNEL}")
        print(f"   - Servo Derecho en Canal: {MOTOR_RIGHT_CHANNEL}")
    except Exception as e:
        print(f"\n❌ Error de inicialización física: {e}")
        print("Comprueba que el HAT esté bien conectado físicamente a la Raspberry Pi y alimentado por batería.")
        sys.exit(1)

    try:
        while True:
            print_menu()
            user_input = input().strip().lower()

            if user_input == 'q':
                print("\nSaliendo de la prueba...")
                break

            elif user_input == 'w':
                # Avanzar
                left_speed = 0.5
                right_speed = 0.5
                print("\n🚀 Comando: AVANZAR (Throttle: Izq=0.5, Der=0.5)")
                
            elif user_input == 's':
                # Retroceder
                left_speed = -0.5
                right_speed = -0.5
                print("\n🐢 Comando: RETROCEDER (Throttle: Izq=-0.5, Der=-0.5)")

            elif user_input == 'a':
                # Girar Izquierda
                left_speed = -0.5
                right_speed = 0.5
                print("\n↪️ Comando: GIRAR IZQUIERDA (Throttle: Izq=-0.5, Der=0.5)")

            elif user_input == 'd':
                # Girar Derecha
                left_speed = 0.5
                right_speed = -0.5
                print("\n↩️ Comando: GIRAR DERECHA (Throttle: Izq=0.5, Der=-0.5)")

            elif user_input in ['', ' ', 'x']:
                # Parar (liberando señal PWM)
                left_speed = None
                right_speed = None
                print("\n🛑 Comando: DETENER (Apagando señal)")

            elif user_input == 'c':
                # Prueba de punto muerto
                print("\n🎯 ENTRENAMIENTO/CALIBRACIÓN DE PUNTO MUERTO:")
                print("Estableciendo duty_cycle = 0 en ambos canales para apagar la señal.")
                pca.channels[MOTOR_LEFT_CHANNEL].duty_cycle = 0
                pca.channels[MOTOR_RIGHT_CHANNEL].duty_cycle = 0
                input("\nPresiona Enter para volver al menú principal...")
                continue
            else:
                print("\n⚠️ Opción no reconocida.")
                continue

            # Enviar señal o apagar canal
            if left_speed is None:
                pca.channels[MOTOR_LEFT_CHANNEL].duty_cycle = 0
                str_left = "Apagado (0V)"
            else:
                final_left = -left_speed if INVERT_LEFT else left_speed
                final_left = max(-1.0, min(1.0, final_left + TRIM_LEFT))
                
                # Boost del servo izquierdo al avanzar (sentido positivo)
                if final_left > 0.0:
                    final_left = min(1.0, final_left * BOOST_LEFT_FORWARD)
                
                servo_left.throttle = final_left
                str_left = f"{final_left:.2f}"

            if right_speed is None:
                pca.channels[MOTOR_RIGHT_CHANNEL].duty_cycle = 0
                str_right = "Apagado (0V)"
            else:
                final_right = -right_speed if INVERT_RIGHT else right_speed
                final_right = max(-1.0, min(1.0, final_right + TRIM_RIGHT))
                servo_right.throttle = final_right
                str_right = f"{final_right:.2f}"

            print(f"   Signals enviadas -> Servo Izq: {str_left} | Servo Der: {str_right}")

    except KeyboardInterrupt:
        print("\nPrueba interrumpida por teclado.")
    finally:
        # Apagado de seguridad
        print("\n🛑 Deteniendo motores por seguridad...")
        try:
            pca.channels[MOTOR_LEFT_CHANNEL].duty_cycle = 0
            pca.channels[MOTOR_RIGHT_CHANNEL].duty_cycle = 0
            pca.deinit()
            print("👋 Desconectado.")
        except Exception:
            pass


if __name__ == '__main__':
    main()
