"""Start the two student nodes AFTER verifying AMCL and undocking.

Nav2/simulation remain in navigation.launch.py. An explicit Python interpreter
keeps YOLO dependencies in a venv while retaining apt-installed cv_bridge.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration as LC
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('turtlebot4_slam_nav')
    detector = Node(package='turtlebot4_slam_nav', executable='yolo_detector.py', name='yolo_detector',
                    prefix=[LC('python_executable')], output='screen',
                    parameters=[LC('yolo_params'), {'model': LC('model'),
                                'show_window': ParameterValue(LC('show_window'), value_type=bool)}])
    return LaunchDescription([
        DeclareLaunchArgument('waypoints', default_value=os.path.join(pkg, 'config', 'waypoints.yaml')),
        DeclareLaunchArgument('yolo_params', default_value=os.path.join(pkg, 'config', 'yolo.yaml')),
        DeclareLaunchArgument('python_executable', default_value='/usr/bin/python3'),
        DeclareLaunchArgument('model', default_value='yolov8n.pt'),
        DeclareLaunchArgument('show_window', default_value='false', choices=['true', 'false']),
        RegisterEventHandler(OnProcessExit(target_action=detector, on_exit=[
            EmitEvent(event=Shutdown(reason='YOLO detector exited; stopping autonomy nodes'))])),
        detector,
        Node(package='turtlebot4_slam_nav', executable='waypoint_navigator.py',
             name='waypoint_navigator', output='screen', parameters=[LC('waypoints')]),
    ])
