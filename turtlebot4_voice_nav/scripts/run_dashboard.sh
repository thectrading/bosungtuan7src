#!/usr/bin/env bash
set -eo pipefail
task_package="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task_workspace="$(cd -- "$task_package/../.." && pwd)"
source /opt/ros/humble/setup.bash
source "$task_workspace/install/setup.bash"
source "$task_workspace/src/turtlebot4_slam_nav/scripts/lab_env.bash"
exec "$task_workspace/.venv-tb4-voice/bin/python" -m turtlebot4_voice_nav.dashboard \
  --artifacts "$task_package/artifacts/user_demo" "$@"
