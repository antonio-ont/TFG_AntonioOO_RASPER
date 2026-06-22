from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([

        # Parámetros de velocidad
        DeclareLaunchArgument('max_linear_speed',  default_value='0.5'),
        DeclareLaunchArgument('max_angular_speed', default_value='1.0'),

        # Calibración de servos (ajustar si no paran en throttle=0)
        DeclareLaunchArgument('trim_left',   default_value='0.0',
            description='Ajuste fino del punto muerto del servo izquierdo'),
        DeclareLaunchArgument('trim_right',  default_value='0.0',
            description='Ajuste fino del punto muerto del servo derecho'),
        DeclareLaunchArgument('invert_left', default_value='false',
            description='Invertir servo izquierdo (montaje en espejo)'),
        DeclareLaunchArgument('invert_right', default_value='true',
            description='Invertir servo derecho (montaje en espejo)'),
        DeclareLaunchArgument('boost_left_forward', default_value='1.5',
            description='Multiplicador de potencia del servo izquierdo al avanzar'),

        # Nodo controlador de ruedas
        Node(
            package='robot_driver',
            executable='wheel_controller',
            name='wheel_controller',
            parameters=[{
                'max_linear_speed':  LaunchConfiguration('max_linear_speed'),
                'max_angular_speed': LaunchConfiguration('max_angular_speed'),
                'trim_left':         LaunchConfiguration('trim_left'),
                'trim_right':        LaunchConfiguration('trim_right'),
                'invert_left':       LaunchConfiguration('invert_left'),
                'invert_right':      LaunchConfiguration('invert_right'),
                'boost_left_forward': LaunchConfiguration('boost_left_forward'),
            }],
            output='screen'
        ),

        # Rosbridge — puente WebSocket para la app de control
        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            name='rosbridge_websocket',
            parameters=[{'port': 9090}],
            output='screen'
        ),
    ])
