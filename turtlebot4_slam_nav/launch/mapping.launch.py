"""Simulation and SLAM Toolbox; no AMCL or autonomous navigation."""
import os
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration as LC


def generate_launch_description():
    pkg = share('turtlebot4_slam_nav')
    return LaunchDescription([
        DeclareLaunchArgument('start_sim', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('slam_params', default_value=os.path.join(pkg, 'config', 'slam.yaml')),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'simulation.launch.py')),
                                 condition=IfCondition(LC('start_sim'))),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(share('turtlebot4_navigation'), 'launch', 'slam.launch.py')),
            launch_arguments={'use_sim_time': 'true', 'sync': 'true', 'params': LC('slam_params')}.items()),
    ])
