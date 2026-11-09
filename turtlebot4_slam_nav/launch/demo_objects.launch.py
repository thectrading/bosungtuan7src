"""Add a real rendered/collidable chair without replacing the saved-map world."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration as LC
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('turtlebot4_slam_nav')
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='maze'),
        Node(package='ros_gz_sim', executable='create', output='screen', arguments=[
            '-world', LC('world'), '-name', 'demo_chair',
            '-file', os.path.join(pkg, 'models', 'demo_chair.sdf'),
            '-x', '-2.5', '-y', '0.5', '-z', '0.0', '-Y', '0.0']),
    ])
