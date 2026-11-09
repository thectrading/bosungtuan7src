"""A partial route must never start navigation before the destination is spoken."""
import json
import unittest
from turtlebot4_voice_nav.speech import UtteranceDecoder, grammar_json


class FakeRecognizer:
    def __init__(self):
        self.text, self.endpoint, self.final_calls = 'đi đến khu vực a', False, 0
    def SetWords(self, value): pass
    def SetPartialWords(self, value): pass
    def AcceptWaveform(self, data): return self.endpoint
    def Reset(self): pass
    def PartialResult(self):
        return json.dumps(dict(partial=self.text, partial_result=[dict(word=w, conf=.99) for w in self.text.split()]))
    def Result(self):
        return json.dumps(dict(text=self.text, result=[dict(word=w, conf=.99) for w in self.text.split()]))
    def FinalResult(self):
        self.final_calls += 1
        return self.Result()


class DecoderTests(unittest.TestCase):
    def test_runtime_grammar_keeps_real_vietnamese_unicode(self):
        grammar = grammar_json()
        self.assertIn('đi đến phòng thí nghiệm', grammar)
        self.assertNotIn('\\u', grammar)

    def test_no_partial_navigation_even_if_stable(self):
        recognizer, events = FakeRecognizer(), []
        decoder = UtteranceDecoder(recognizer, lambda *a, **k: events.append(a))
        for _ in range(25): decoder.push(b'\0'*4000)
        self.assertFalse(any(e[0] == 'command' for e in events))
        recognizer.text = 'di chuyển từ khu vực a đến khu vực bê'
        recognizer.endpoint = True
        decoder.push(b'\0'*4000)
        commands = [e for e in events if e[0] == 'command']
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][1], recognizer.text)

    def test_forced_endpoint_after_eight_seconds_and_unknown_is_preserved(self):
        recognizer, events = FakeRecognizer(), []
        recognizer.text = 'đi đến [unk] a'
        decoder = UtteranceDecoder(recognizer, lambda *a, **k: events.append(a))
        for _ in range(64): decoder.push(b'\0'*4000)
        self.assertEqual(recognizer.final_calls, 1)
        commands = [e for e in events if e[0] == 'command']
        self.assertIn('[unk]', commands[0][1])


if __name__ == '__main__': unittest.main(verbosity=2)
