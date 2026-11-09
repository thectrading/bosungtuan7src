#!/usr/bin/env python3
"""Create an optional model overlay that selects Ogre 2 for Fortress sensors.

The installed model uses Ogre 1. On this Intel GPU it produced only minimum ranges.
This copies the upstream description and changes that one rendering setting, without
modifying /opt/ros, physics, controllers, sensor poses, ranges or world geometry.
"""
import argparse
import os
import shutil
from pathlib import Path
from ament_index_python.packages import get_package_share_directory


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=os.path.expanduser('~/.cache/turtlebot4_slam_nav/ogre2'))
    args=parser.parse_args()
    prefix=Path(args.output).resolve()
    source=Path(get_package_share_directory('irobot_create_description')).resolve()
    target=prefix/'share/irobot_create_description'
    if source == target.resolve():
        print(f'Overlay already active: {prefix}')
        return
    text=(source/'urdf/create3.urdf.xacro').read_text()
    if '<render_engine>ogre</render_engine>' not in text:
        raise RuntimeError('Expected the upstream Humble Ogre 1 setting; inspect this model version first.')
    # Only reuse directories created by this helper.
    marker=prefix/'GENERATED_BY_TURTLEBOT4_SLAM_NAV'
    if prefix.exists() and not marker.exists():
        raise RuntimeError(f'Existing unowned directory: {prefix}; choose another --output.')
    prefix.mkdir(parents=True,exist_ok=True)
    marker.write_text(f'Upstream: {source}\nOnly modification: render_engine ogre -> ogre2\n')
    shutil.copytree(source,target,dirs_exist_ok=True)
    (target/'urdf/create3.urdf.xacro').write_text(text.replace('<render_engine>ogre</render_engine>','<render_engine>ogre2</render_engine>'))
    index=prefix/'share/ament_index/resource_index/packages/irobot_create_description'
    index.parent.mkdir(parents=True,exist_ok=True)
    index.write_text('')
    print(f'Created model overlay: {prefix}')
    print(f'For each terminal: export AMENT_PREFIX_PATH="{prefix}:$AMENT_PREFIX_PATH"')


if __name__=='__main__':main()
