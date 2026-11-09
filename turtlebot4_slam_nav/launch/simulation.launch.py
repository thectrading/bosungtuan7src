"""Use the official Fortress world, robot, sensors and Create 3 controllers."""
import os
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, GroupAction, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration as LC
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    tb = share('turtlebot4_ignition_bringup')
    pkg = share('turtlebot4_slam_nav')
    resource = os.pathsep.join([
        os.path.join(tb, 'worlds'),
        os.path.join(share('irobot_create_ignition_bringup'), 'worlds'),
        os.path.dirname(share('turtlebot4_description')),
        os.path.dirname(share('irobot_create_description')),
        os.environ.get('IGN_GAZEBO_RESOURCE_PATH', ''),
    ])
    gui_plugins = os.pathsep.join([
        os.path.join(share('turtlebot4_ignition_gui_plugins'), 'lib'),
        os.path.join(share('irobot_create_ignition_plugins'), 'lib'),
        os.environ.get('IGN_GUI_PLUGIN_PATH', ''),
    ])
    system_plugins = os.pathsep.join([
        os.environ.get('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', ''),
        os.environ.get('LD_LIBRARY_PATH', ''),
    ])
    args = [DeclareLaunchArgument('world', default_value='maze', choices=['maze', 'warehouse', 'depot']),
            DeclareLaunchArgument('model', default_value='lite', choices=['lite', 'standard']),
            DeclareLaunchArgument('gui', default_value='true', choices=['true', 'false']),
            DeclareLaunchArgument('headless_rendering', default_value='false', choices=['true', 'false']),
            DeclareLaunchArgument('rviz', default_value='true', choices=['true', 'false']),
            DeclareLaunchArgument('rviz_use_sim_time', default_value='true', choices=['true', 'false']),
            DeclareLaunchArgument('rviz_config', default_value=os.path.join(pkg, 'rviz', 'lab.rviz')),
            DeclareLaunchArgument('use_sim_time', default_value='true', choices=['true'])]
    args += [DeclareLaunchArgument(p, default_value='0.0') for p in ('x', 'y', 'yaw')]
    # The stock top-level launch does not forward every spawn option on older Humble releases.
    # Include its server and spawn components explicitly, without replacing any controller.
    # Direct argv also lets ROS launch stop Gazebo without an intermediate shell.
    gazebo_gui = ExecuteProcess(
        cmd=['ign', 'gazebo', [LC('world'), '.sdf'], '-r', '-v', '3',
             '--gui-config', [tb, '/gui/', LC('model'), '/gui.config']],
        output='screen', condition=IfCondition(LC('gui')))
    gazebo_server = GroupAction([
        ExecuteProcess(cmd=['ign', 'gazebo', [LC('world'), '.sdf'], '-r', '-s', '-v', '3'],
                       output='screen', condition=UnlessCondition(LC('headless_rendering'))),
        ExecuteProcess(cmd=['ign', 'gazebo', [LC('world'), '.sdf'], '-r', '-s', '-v', '3',
                            '--headless-rendering', '--render-engine-server', 'ogre2'],
                       output='screen', condition=IfCondition(LC('headless_rendering'))),
    ], condition=UnlessCondition(LC('gui')))
    robot = GroupAction([IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(tb, 'launch', 'turtlebot4_spawn.launch.py')),
        launch_arguments={**{k: LC(k) for k in ('model', 'x', 'y', 'yaw', 'use_sim_time')},
                          'rviz': 'false', 'slam': 'false', 'localization': 'false', 'nav2': 'false'}.items())])
    return LaunchDescription(args + [
        SetEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', resource),
        SetEnvironmentVariable('IGN_GUI_PLUGIN_PATH', gui_plugins),
        SetEnvironmentVariable('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', system_plugins),
        gazebo_gui, gazebo_server, robot,
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='clock_bridge',
             arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'], output='screen'),
        Node(package='rviz2', executable='rviz2', name='rviz2',
             arguments=['-d', LC('rviz_config')],
             parameters=[{'use_sim_time': ParameterValue(LC('rviz_use_sim_time'), value_type=bool)}],
             condition=IfCondition(LC('rviz'))),
    ])
