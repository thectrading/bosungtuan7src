"""Restart the same world, load our saved map and localize with AMCL."""
import os
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration as LC


def check_map(context):
    path = LC('map').perform(context)
    if not os.path.isfile(path):
        raise RuntimeError(f'Map does not exist: {path}. Run mapping, then save_map.sh first.')
    return []


def generate_launch_description():
    pkg = share('turtlebot4_slam_nav')
    return LaunchDescription([
        DeclareLaunchArgument('start_sim', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('map', default_value=os.path.join(pkg, 'maps', 'map.yaml')),
        DeclareLaunchArgument('localization_params', default_value=os.path.join(pkg, 'config', 'localization.yaml')),
        OpaqueFunction(function=check_map),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'simulation.launch.py')),
                                 condition=IfCondition(LC('start_sim'))),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(share('turtlebot4_navigation'), 'launch', 'localization.launch.py')),
            launch_arguments={'use_sim_time': 'true', 'map': LC('map'), 'params': LC('localization_params')}.items()),
    ])
