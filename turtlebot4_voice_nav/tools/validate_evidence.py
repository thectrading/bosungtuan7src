"""Validate real Nav2/Gazebo results; ground truth is read-only sampled evidence."""
from collections import Counter
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from irobot_create_msgs.msg import HazardDetection


def main():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root/'artifacts/integration_results.json').read_text())
    assert data['all_succeeded']
    commands = data['commands']
    assert len(commands) == 5
    for command in commands:
        if command['expected_route']:
            assert command['result'] == 'ROUTE_SUCCEEDED'
            assert command['completed_in_order'] == command['expected_route']
            assert all(error <= .4 for error in command['goal_errors_m'])
        else:
            assert command['result'] == 'REJECTED_UNKNOWN_REGION'
    route = next(c for c in commands if c['expected_route'] == ['A', 'B'])
    assert route['completed_in_order'] == ['A', 'B']
    counts = Counter(t for event in data['hazards'] for t in event['types'])
    for hazard in (HazardDetection.BUMP, HazardDetection.CLIFF, HazardDetection.STALL, HazardDetection.WHEEL_DROP):
        assert counts[hazard] == 0
    boxes = []
    world = Path(get_package_share_directory('turtlebot4_ignition_bringup'))/'worlds/maze.sdf'
    for model in ET.parse(world).findall('.//world/model'):
        if model.get('name') not in {'obstacles', 'border'}: continue
        for link in model.findall('link'):
            x, y, *_ = map(float, link.findtext('pose').split())
            sx, sy, *_ = map(float, link.findtext('collision/geometry/box/size').split())
            boxes.append((x-sx/2, x+sx/2, y-sy/2, y+sy/2))
    clearance = [min(math.hypot(max(xmin-x, 0, x-xmax), max(ymin-y, 0, y-ymax))
                     for xmin, xmax, ymin, ymax in boxes) for stamp, x, y in data['ground_truth']]
    assert clearance and min(clearance) > .175
    summary = dict(real_nav2_routes_succeeded=4, real_nav2_goals_succeeded=5,
                   unknown_region_rejected=True, source_then_destination_order_verified=True,
                   audio_source='SYNTHETIC_GOOGLE_TTS_AUDIO',
                   arrival_errors_m=[error for c in commands for error in c.get('goal_errors_m', [])],
                   max_arrival_error_m=max(error for c in commands for error in c.get('goal_errors_m', [])),
                   hazard_counts=dict(counts), sampled_ground_truth_points=len(clearance),
                   min_sampled_center_to_maze_wall_m=min(clearance),
                   method='Action status 4 + TF errors, sampled read-only Gazebo ground truth and driver hazards; not continuous collision proof or human speech accuracy.')
    (root/'artifacts/validation.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()
