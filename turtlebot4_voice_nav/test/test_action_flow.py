"""ROS action tests with a mock server, NOT physical/simulator navigation evidence."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import queue

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String

from turtlebot4_voice_nav.navigator import VoiceNavigator

ROOT = Path(__file__).resolve().parents[1]


class MockNav2(Node):
    def __init__(self):
        super().__init__('mock_nav2_for_voice_tests')
        self.mode, self.sent, self.pose = 'success', [], [0., 0., 0.]
        self.arrived = threading.Event()
        self.server = ActionServer(self, NavigateToPose, '/navigate_to_pose', self.execute,
                                   goal_callback=self.accept, cancel_callback=lambda _: CancelResponse.ACCEPT,
                                   callback_group=ReentrantCallbackGroup())

    def accept(self, request):
        self.sent.append((request.pose.pose.position.x, request.pose.pose.position.y))
        self.arrived.set()
        if self.mode == 'delay_accept':
            time.sleep(.6)
        return GoalResponse.REJECT if self.mode == 'reject' else GoalResponse.ACCEPT

    def execute(self, handle):
        deadline = time.monotonic()+(2 if self.mode in {'wait', 'delay_accept'} else .1)
        while time.monotonic() < deadline:
            if handle.is_cancel_requested:
                handle.canceled(); return NavigateToPose.Result()
            time.sleep(.02)
        if self.mode == 'abort':
            handle.abort()
        else:
            p = handle.request.pose.pose.position
            self.pose = [p.x, p.y, 0.]
            handle.succeed()
        return NavigateToPose.Result()


class ActionFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='voice-nav-action-test-')
        rclpy.init(args=['--ros-args', '-p', 'regions_file:='+str(ROOT/'maps/regions.json'),
                         '-p', 'log_file:='+str(Path(cls.tmp.name)/'events.jsonl')])
        cls.server, cls.nav = MockNav2(), VoiceNavigator()
        cls.nav.readiness = lambda: ''
        cls.nav.read_pose = lambda: cls.server.pose
        cls.calls = queue.Queue()
        def dispatch():
            while not cls.calls.empty():
                fn, done = cls.calls.get_nowait()
                try: fn()
                finally: done.set()
        cls.guard = cls.nav.create_guard_condition(dispatch)
        cls.nav.client.wait_for_server(timeout_sec=3)
        cls.executor = MultiThreadedExecutor(num_threads=4)
        cls.executor.add_node(cls.server); cls.executor.add_node(cls.nav)
        cls.thread = threading.Thread(target=cls.executor.spin, daemon=True); cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.executor.shutdown()
        cls.thread.join(timeout=3)
        cls.server.destroy_node(); cls.nav.destroy_node(); rclpy.shutdown(); cls.tmp.cleanup()

    def setUp(self):
        self.wait(lambda: not self.nav.busy)
        self.server.sent.clear(); self.server.arrived.clear(); self.server.mode = 'success'
        def reset():
            self.nav.state, self.nav.cancel_requested = 'IDLE', False
        self.on_executor(reset)

    def wait(self, predicate, seconds=5):
        deadline = time.monotonic()+seconds
        while not predicate() and time.monotonic() < deadline: time.sleep(.02)
        self.assertTrue(predicate(), 'Action workflow timed out')

    def send(self, text):
        self.on_executor(lambda: self.nav.command_callback(String(data=text)))

    def on_executor(self, function):
        done = threading.Event()
        self.calls.put((function, done)); self.guard.trigger()
        self.assertTrue(done.wait(3))

    def test_ordered_source_then_destination_even_when_elsewhere(self):
        self.server.pose = [-2., 4., 0.]
        self.send('Di chuyển từ khu vực A đến khu vực B')
        self.wait(lambda: self.nav.state == 'SUCCEEDED')
        self.assertEqual(self.server.sent, [(-2., -3.), (2., -3.)])
        self.assertEqual(self.nav.completed, ['A', 'B'])

    def test_unknown_route_has_zero_goals(self):
        self.send('Đi từ A qua Z rồi đến B')
        self.assertFalse(self.server.sent)
        self.assertFalse(self.nav.busy)

    def test_rejected_first_goal_stops_remaining_route(self):
        self.server.mode = 'reject'
        self.send('Đi từ A đến B')
        self.wait(lambda: self.nav.state == 'FAILED')
        self.assertEqual(self.server.sent, [(-2., -3.)])

    def test_aborted_first_goal_stops_remaining_route(self):
        self.server.mode = 'abort'
        self.send('Đi từ A đến B')
        self.wait(lambda: self.nav.state == 'FAILED')
        self.assertEqual(self.server.sent, [(-2., -3.)])

    def test_cancel_before_acceptance_cancels_late_handle(self):
        self.server.mode = 'delay_accept'
        self.send('Đi từ A đến B')
        self.wait(lambda: self.server.arrived.is_set())
        self.send('Dừng lại')
        self.wait(lambda: self.nav.state == 'CANCELED')
        self.assertEqual(self.server.sent, [(-2., -3.)])

    def test_low_confidence_microphone_sends_no_goal(self):
        self.send(json.dumps(dict(text='Đi đến A', source='MICROPHONE', confidence=.4)))
        self.assertFalse(self.server.sent)


if __name__ == '__main__':
    unittest.main(verbosity=2)
