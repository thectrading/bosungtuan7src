#!/usr/bin/env python3
"""Initialize localization/undock ONLY in the newly launched maze simulator.

Ground truth is read-only for the initial pose, never a navigation controller.
"""
import math
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from irobot_create_msgs.msg import DockStatus
from irobot_create_msgs.action import Undock


def main():
    rclpy.init()
    node = rclpy.create_node('voice_nav_sim_preparation', parameter_overrides=[rclpy.parameter.Parameter('use_sim_time', value=True)])
    ground, dock = [], []
    node.create_subscription(Odometry, '/sim_ground_truth_pose', lambda m: ground.append(m), qos_profile_sensor_data)
    node.create_subscription(DockStatus, '/dock_status', lambda m: dock.append(m), qos_profile_sensor_data)
    publisher = node.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
    def wait(predicate, seconds=90):
        deadline = time.monotonic()+seconds
        while not predicate() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
        if not predicate():
            raise TimeoutError('Simulation telemetry timeout')
    def pose():
        wait(lambda: bool(ground))
        message = PoseWithCovarianceStamped()
        message.header.frame_id = 'map'
        message.header.stamp = node.get_clock().now().to_msg()
        message.pose.pose = ground[-1].pose.pose
        message.pose.covariance[0] = message.pose.covariance[7] = .04
        message.pose.covariance[35] = .04
        for _ in range(5):
            publisher.publish(message)
            rclpy.spin_once(node, timeout_sec=.3)
        p = message.pose.pose.position
        print(f'INITIAL_POSE from simulation: {p.x:.3f}, {p.y:.3f}', flush=True)
    try:
        wait(lambda: ground and dock)
        if not node.get_parameter('use_sim_time').value:
            raise RuntimeError('Simulation only')
        pose()
        if dock[-1].is_docked:
            client = ActionClient(node, Undock, '/undock')
            if not client.wait_for_server(timeout_sec=20):
                raise RuntimeError('No undock action')
            future = client.send_goal_async(Undock.Goal())
            wait(future.done, 20)
            handle = future.result()
            if not handle.accepted:
                raise RuntimeError('Undock rejected')
            result = handle.get_result_async()
            wait(result.done, 120)
            if result.result().status != 4:
                raise RuntimeError('Undock failed')
            print('UNDOCK SUCCEEDED', flush=True)
        deadline = time.monotonic()+2
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
        pose()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
