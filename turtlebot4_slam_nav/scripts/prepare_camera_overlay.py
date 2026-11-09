#!/usr/bin/env python3
"""Copy the official camera description and cap RGB-D update rate for this host.

Geometry, camera poses, image resolution, LiDAR, physics and controllers remain
the official model. No file under /opt/ros is modified.
"""
import argparse
import os
from pathlib import Path
import re
import shutil

from ament_index_python.packages import get_package_share_directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rate', type=int, default=10)
    parser.add_argument('--output', type=Path,
                        default=Path.home()/'.cache/turtlebot4_slam_nav/camera')
    args = parser.parse_args()
    if args.rate < 1 or args.rate > 30:
        raise ValueError('Camera rate must be between 1 and 30 Hz')
    prefix = args.output.expanduser().resolve()
    target = prefix/'share/turtlebot4_description'
    marker = prefix/'GENERATED_CAMERA_OVERLAY'
    source = Path(get_package_share_directory('turtlebot4_description')).resolve()
    if source == target:
        candidates = [Path(p)/'share/turtlebot4_description'
                      for p in os.environ.get('AMENT_PREFIX_PATH', '').split(os.pathsep)
                      if p and Path(p).resolve() != prefix]
        source = next((p.resolve() for p in candidates if (p/'urdf/sensors/oakd.urdf.xacro').is_file()), None)
        if source is None:
            raise RuntimeError('Cannot find original turtlebot4_description outside this overlay')
    if prefix.exists() and not marker.exists():
        raise RuntimeError(f'Refusing to replace an unowned directory: {prefix}')
    camera = source/'urdf/sensors/oakd.urdf.xacro'
    text, count = re.subn(r'<update_rate>30</update_rate>',
                          f'<update_rate>{args.rate}</update_rate>', camera.read_text())
    if count != 1:
        raise RuntimeError('Expected one 30 Hz OAK-D sensor; inspect this simulator version')
    prefix.mkdir(parents=True, exist_ok=True)
    marker.write_text(f'Upstream: {source}\nOnly modification: OAK-D update_rate 30 -> {args.rate} Hz\n')
    shutil.copytree(source, target, dirs_exist_ok=True)
    (target/'urdf/sensors/oakd.urdf.xacro').write_text(text)
    index = prefix/'share/ament_index/resource_index/packages/turtlebot4_description'
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text('')
    print(f'Camera overlay: {prefix}, update_rate={args.rate} Hz. Source lab_env.bash and restart simulation.')


if __name__ == '__main__':
    main()
