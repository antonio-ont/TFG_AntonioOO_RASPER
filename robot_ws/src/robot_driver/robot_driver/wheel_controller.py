import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from geometry_msgs.msg import Twist

try:
    import board, busio
    from adafruit_pca9685 import PCA9685
    from adafruit_motor import servo
    HARDWARE_AVAILABLE = True
except (ImportError, NotImplementedError):
    HARDWARE_AVAILABLE = False

# Canales del HAT donde se conectan los servos
MOTOR_LEFT_CHANNEL  = 7
MOTOR_RIGHT_CHANNEL = 8


class WheelController(Node):
    def __init__(self):
        super().__init__('wheel_controller')

        # Parámetros configurables desde launch file o línea de comandos
        self.declare_parameter('max_linear_speed', 0.5)
        self.declare_parameter('max_angular_speed', 1.0)
        self.declare_parameter('trim_left', 0.0)   # Ajuste fino del punto muerto servo izq
        self.declare_parameter('trim_right', 0.0)   # Ajuste fino del punto muerto servo der
        self.declare_parameter('invert_left', False)  # Invertir servo izq (montaje espejo)
        self.declare_parameter('invert_right', True)  # Invertir servo der (montaje espejo)
        self.declare_parameter('boost_left_forward', 1.5) # Compensar velocidad del servo izquierdo

        self.max_lin    = self.get_parameter('max_linear_speed').value
        self.max_ang    = self.get_parameter('max_angular_speed').value
        self.trim_left  = self.get_parameter('trim_left').value
        self.trim_right = self.get_parameter('trim_right').value
        self.invert_left = self.get_parameter('invert_left').value
        self.invert_right = self.get_parameter('invert_right').value
        self.boost_left_forward = self.get_parameter('boost_left_forward').value

        # Configuración de Calidad de Servicio (QoS) para seguridad activa (ISO 13482:2014)
        qos_profile = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE
        )

        # Suscripción al tópico de velocidad con QoS de control rápido
        self.sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, qos_profile)

        # Monitoreo de latido (Heartbeat Watchdog) para parada de seguridad
        self.last_cmd_time = self.get_clock().now()
        self.watchdog_timer = self.create_timer(0.1, self.watchdog_callback) # 10 Hz (cada 100 ms)

        # Inicialización del hardware
        self.servo_left  = None
        self.servo_right = None
        self.pca = None

        if HARDWARE_AVAILABLE:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                self.pca = PCA9685(i2c)
                self.pca.frequency = 50  # 50 Hz estándar para servos

                self.servo_left  = servo.ContinuousServo(
                    self.pca.channels[MOTOR_LEFT_CHANNEL])
                self.servo_right = servo.ContinuousServo(
                    self.pca.channels[MOTOR_RIGHT_CHANNEL])

                # Parar los servos al arrancar apagando señal PWM a bajo nivel
                self.pca.channels[MOTOR_LEFT_CHANNEL].duty_cycle = 0
                self.pca.channels[MOTOR_RIGHT_CHANNEL].duty_cycle = 0

                self.get_logger().info('✅ HAT PCA9685 detectado — modo hardware')
                self.get_logger().info(
                    f'   Servos en canales {MOTOR_LEFT_CHANNEL} (izq) '
                    f'y {MOTOR_RIGHT_CHANNEL} (der)')
            except Exception as e:
                self.get_logger().error(f'❌ Error al inicializar el HAT: {e}')
                self.pca = None
                self.servo_left = None
                self.servo_right = None
        else:
            self.get_logger().warn('⚠️  Hardware no disponible — modo simulado')

        self.get_logger().info('Escuchando /cmd_vel...')

    def cmd_vel_callback(self, msg: Twist):
        self.last_cmd_time = self.get_clock().now()
        linear  = msg.linear.x
        angular = msg.angular.z

        # Modelo cinemático diferencial: vL = v - ω, vR = v + ω
        left_speed  = linear - angular
        right_speed = linear + angular

        # Normalizar al rango [-1.0, +1.0]
        max_val = max(abs(left_speed), abs(right_speed), 1.0)
        left_speed  /= max_val
        right_speed /= max_val

        self.get_logger().info(
            f'L={left_speed:+.2f}  R={right_speed:+.2f}')

        self.set_servo(left_speed, right_speed)

    def watchdog_callback(self):
        # Medir tiempo desde el último comando de velocidad en segundos
        time_since_last_cmd = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9
        if time_since_last_cmd > 0.5:
            # Failsafe activo: detener motores apagando PWM
            if self.servo_left is not None or self.servo_right is not None:
                self.set_servo(0.0, 0.0)

    def set_servo(self, left: float, right: float):
        """Envía throttle a los servos de rotación continua.

        throttle: -1.0 = máxima velocidad reversa
                   0.0 = parado
                  +1.0 = máxima velocidad adelante
        """
        # Guardar si el sentido original es hacia adelante para aplicar el boost correcto
        is_forward_left = left > 0.0

        # Invertir servo izquierdo si está montado en espejo
        if self.invert_left:
            left = -left
        
        # Invertir servo derecho si está montado en espejo
        if self.invert_right:
            right = -right

        # Aplicar trim de calibración y clampear a [-1.0, 1.0]
        left  = max(-1.0, min(1.0, left  + self.trim_left))
        right = max(-1.0, min(1.0, right + self.trim_right))

        # Boost del servo izquierdo al avanzar (basado en el sentido positivo original)
        if is_forward_left:
            left = max(-1.0, min(1.0, left * self.boost_left_forward))

        if self.servo_left is not None:
            if abs(left) < 0.01:
                self.pca.channels[MOTOR_LEFT_CHANNEL].duty_cycle = 0
            else:
                self.servo_left.throttle = left

        if self.servo_right is not None:
            if abs(right) < 0.01:
                self.pca.channels[MOTOR_RIGHT_CHANNEL].duty_cycle = 0
            else:
                self.servo_right.throttle = right

    def destroy_node(self):
        """Parar los servos y apagar el HAT antes de cerrar."""
        self.get_logger().info('Apagando motores...')
        if self.pca is not None:
            self.pca.channels[MOTOR_LEFT_CHANNEL].duty_cycle = 0
            self.pca.channels[MOTOR_RIGHT_CHANNEL].duty_cycle = 0
            self.pca.deinit()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WheelController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
