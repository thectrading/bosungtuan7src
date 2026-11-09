#!/usr/bin/env bash
set -eo pipefail
task_package="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task_workspace="$(cd -- "$task_package/../.." && pwd)"
source /opt/ros/humble/setup.bash
source "$task_workspace/install/setup.bash"
source "$task_workspace/src/turtlebot4_slam_nav/scripts/lab_env.bash"
exec ros2 launch turtlebot4_slam_nav navigation.launch.py world:=maze \
  map:="$task_package/maps/map.yaml" gui:=true rviz:=true rviz_use_sim_time:=false "$@"
