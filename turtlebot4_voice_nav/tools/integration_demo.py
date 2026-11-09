#!/usr/bin/env python3
"""Cached SYNTHETIC audio → real Vosk → real Nav2/Gazebo, with honest provenance.

No cmd_vel, no fake position, no map/AMCL reset. Start already localized/undocked.
"""
import argparse
import json
from pathlib import Path
import time
import wave

import rclpy
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String
from nav_msgs.msg import Odometry
from irobot_create_msgs.msg import HazardDetectionVector

from synthetic_speech import recognize
from turtlebot4_voice_nav.commands import RegionCatalog
from turtlebot4_voice_nav.speech import MODEL_PATH, GRAMMAR


def main():
    from vosk import Model, SetLogLevel
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', required=True)
    parser.add_argument('--regions', required=True)
    args = parser.parse_args()
    root = Path(args.artifacts)
    audio_root = root/'asr_google'
    samples = json.loads((audio_root/'asr_results.json').read_text())
    SetLogLevel(-1)
    model, catalog = Model(str(MODEL_PATH)), RegionCatalog(args.regions)
    rclpy.init()
    node = rclpy.create_node('voice_nav_integration_demo')
    publisher = node.create_publisher(String, '/voice_nav/command', 10)
    statuses, ground_truth, hazards = [], [], []
    start = time.monotonic()
    evidence = dict(source='CACHED_SYNTHETIC_GOOGLE_TTS_AUDIO_DECODED_BY_VOSK',
                    navigation='REAL_NAV2_ACTIONS_IN_TURTLEBOT4_MAZE_SIMULATOR',
                    started_wall=time.time(), commands=[], statuses=statuses, ground_truth=ground_truth, hazards=hazards)
    last_gt = [0.]
    def status(message):
        data = json.loads(message.data)
        if data.get('event'):
            statuses.append(data)
        current[:] = [data]
    def ground(message):
        if time.monotonic()-last_gt[0] > .5:
            p = message.pose.pose.position
            ground_truth.append([time.monotonic()-start, p.x, p.y])
            last_gt[0] = time.monotonic()
    def hazard(message):
        if message.detections:
            hazards.append(dict(time_s=time.monotonic()-start, types=[d.type for d in message.detections]))
    current = []
    node.create_subscription(String, '/voice_nav/status', status, 50)
    node.create_subscription(Odometry, '/sim_ground_truth_pose', ground, qos_profile_sensor_data)
    node.create_subscription(HazardDetectionVector, '/hazard_detection', hazard, qos_profile_sensor_data)
    def wait(predicate, seconds):
        deadline = time.monotonic()+seconds
        while not predicate() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
        if not predicate(): raise TimeoutError('Timed out waiting for Nav2 integration result')
    try:
        wait(lambda: current and not current[-1].get('ready_reason') and publisher.get_subscription_count() > 0, 30)
        # B before A→B ensures the robot starts elsewhere and MUST visit A first.
        for sample_index in (0, 2, 1, 3, 4):
            sample = samples[sample_index]
            with wave.open(str(audio_root/sample['audio'])) as file:
                pcm = b'\0'*8000+file.readframes(file.getnframes())+b'\0'*32000
            transcript, confidence = recognize(model, pcm, GRAMMAR)
            command = catalog.parse(transcript)
            if list(command.route) != sample['expected_route'] or (command.route and confidence < .65):
                raise AssertionError('Audio was not recognized as expected; never substitute the intended text')
            before = len(statuses)
            row = dict(time_s=time.monotonic()-start, wall_time=time.time(), audio=sample['audio'],
                       spoken=sample['spoken'], transcript=transcript, confidence=confidence,
                       parsed_kind=command.kind, expected_route=sample['expected_route'])
            evidence['commands'].append(row)
            print('ASR_COMMAND', json.dumps(row, ensure_ascii=False), flush=True)
            publisher.publish(String(data=json.dumps(dict(text=transcript, source='SYNTHETIC_AUDIO', confidence=confidence), ensure_ascii=False)))
            if command.route:
                wait(lambda: any(s.get('event') in {'ROUTE_SUCCEEDED', 'GOAL_FAILED', 'FAILED', 'CANCELED', 'GOAL_REJECTED', 'REJECTED_NOT_READY'} for s in statuses[before:]), 600)
                results = [s for s in statuses[before:] if s.get('event') in {'ROUTE_SUCCEEDED', 'GOAL_FAILED', 'FAILED', 'CANCELED', 'GOAL_REJECTED', 'REJECTED_NOT_READY'}]
                result = results[-1]
                row['result'] = result['event']
                if row['result'] != 'ROUTE_SUCCEEDED': raise RuntimeError(result)
                completed = [s.get('region_id') for s in statuses[before:] if s.get('event') == 'GOAL_SUCCEEDED']
                assert completed == sample['expected_route'], completed
                row['completed_in_order'] = completed
                row['goal_errors_m'] = [s['error_m'] for s in statuses[before:] if s.get('event') == 'GOAL_SUCCEEDED']
            else:
                wait(lambda: any(s.get('event') == 'REJECTED' for s in statuses[before:]), 8)
                row['result'] = 'REJECTED_UNKNOWN_REGION'
                assert not any(s.get('event') == 'GOAL_SENT' for s in statuses[before:])
            print('RESULT', json.dumps(row, ensure_ascii=False), flush=True)
            (root/'integration_results.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n')
            pause = time.monotonic()+2
            while time.monotonic() < pause: rclpy.spin_once(node, timeout_sec=.1)
        evidence['all_succeeded'] = True
    except Exception as exc:
        evidence['all_succeeded'], evidence['error'] = False, str(exc)
        publisher.publish(String(data='Dừng lại'))
        raise
    finally:
        evidence['duration_wall_s'] = time.monotonic()-start
        (root/'integration_results.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n')
        node.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
