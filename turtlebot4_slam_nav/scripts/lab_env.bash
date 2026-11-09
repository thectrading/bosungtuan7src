# Source AFTER /opt/ros/humble/setup.bash and your workspace/install/setup.bash.
# Reproduce the host-specific environment used in the validation logs.
export ROS_DOMAIN_ID="${TB4_ROS_DOMAIN_ID:-43}"
export RMW_IMPLEMENTATION="${TB4_RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
export IGN_IP=127.0.0.1
task_tb4_env_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export CYCLONEDDS_URI="file://$task_tb4_env_directory/../config/cyclonedds_local.xml"
unset task_tb4_env_directory
# Prefer the apt installation; the local extraction is a fallback on this host,
# where sudo requires the user's password.
task_tb4_dds_prefix="$HOME/.local/share/tb4_dds/opt/ros/humble"
if [[ -f "$task_tb4_dds_prefix/lib/librmw_cyclonedds_cpp.so" ]]; then
  export AMENT_PREFIX_PATH="$task_tb4_dds_prefix:$AMENT_PREFIX_PATH"
  export LD_LIBRARY_PATH="$task_tb4_dds_prefix/lib:$task_tb4_dds_prefix/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
fi
unset task_tb4_dds_prefix
# Prevent VS Code Snap's GTK modules from loading core20's old libc into RViz.
unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GIO_MODULE_DIR
# SLAM Toolbox treats SNAP_COMMON as proof it is itself running in a snap and
# prepends that directory to serialize paths. These are apt-installed ROS nodes.
unset SNAP_COMMON
export XDG_DATA_DIRS=/usr/local/share:/usr/share
export XDG_CONFIG_DIRS=/etc/xdg
task_tb4_renderer_prefix="$HOME/.cache/turtlebot4_slam_nav/ogre2"
if [[ -f "$task_tb4_renderer_prefix/GENERATED_BY_TURTLEBOT4_SLAM_NAV" ]]; then
  export AMENT_PREFIX_PATH="$task_tb4_renderer_prefix:$AMENT_PREFIX_PATH"
fi
unset task_tb4_renderer_prefix
task_tb4_camera_prefix="$HOME/.cache/turtlebot4_slam_nav/camera"
if [[ -f "$task_tb4_camera_prefix/GENERATED_CAMERA_OVERLAY" ]]; then
  export AMENT_PREFIX_PATH="$task_tb4_camera_prefix:$AMENT_PREFIX_PATH"
fi
unset task_tb4_camera_prefix
