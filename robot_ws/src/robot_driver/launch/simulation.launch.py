import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, SetEnvironmentVariable, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    pkg_dir = get_package_share_directory('robot_driver')
    xacro_file = os.path.join(pkg_dir, 'urdf', 'rasper.urdf.xacro')

    # Procesar xacro → URDF
    robot_description = xacro.process_file(xacro_file).toxml()

    # Declarar argumento para controlar el spawn del robot
    spawn_robot_arg = DeclareLaunchArgument(
        'spawn_robot',
        default_value='true',
        description='Si se establece en true, se spawnea el robot en Gazebo'
    )

    # Gazebo
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('gazebo_ros'),
                'launch', 'gazebo.launch.py'
            )
        ),
        launch_arguments={'verbose': 'true'}.items()
    )

    # Robot State Publisher
    robot_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen'
    )

    # Spawn del robot en Gazebo (condicionado por spawn_robot)
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'rasper',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.1',
            '-timeout', '120.0',
        ],
        condition=IfCondition(LaunchConfiguration('spawn_robot')),
        output='screen'
    )

    # Rosbridge WebSocket para la app web/móvil
    rosbridge = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        parameters=[{'port': 9090}],
        output='screen'
    )

    return LaunchDescription([
        SetEnvironmentVariable(name='GAZEBO_MODEL_DATABASE_URI', value=''),
        spawn_robot_arg,
        gazebo,
        robot_state_pub,
        spawn_robot,
        rosbridge,
    ])
