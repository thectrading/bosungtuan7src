"""Saved-map AMCL and the official TurtleBot 4 Nav2 launch."""
import os
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration as LC


def generate_launch_description():
    pkg = share('turtlebot4_slam_nav')
    return LaunchDescription([
        DeclareLaunchArgument('nav2_params', default_value=os.path.join(pkg, 'config', 'nav2.yaml')),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'localization.launch.py'))),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(share('turtlebot4_navigation'), 'launch', 'nav2.launch.py')),
            launch_arguments={'use_sim_time': 'true', 'params_file': LC('nav2_params')}.items()),
    ])
