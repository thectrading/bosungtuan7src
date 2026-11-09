"""Run cached audio through the EXACT recognizer/decoder used by the microphone."""
import json
from pathlib import Path
import wave

from vosk import Model, SetLogLevel
from turtlebot4_voice_nav.commands import RegionCatalog
from turtlebot4_voice_nav.speech import MODEL_PATH, make_recognizer, UtteranceDecoder


def main():
    root = Path(__file__).resolve().parents[1]
    SetLogLevel(-1)
    model, catalog = Model(str(MODEL_PATH)), RegionCatalog(root/'maps/regions.json')
    evidence = []
    for sample in json.loads((root/'artifacts/asr_google/asr_results.json').read_text()):
        events = []
        decoder = UtteranceDecoder(make_recognizer(model), lambda *a, **k: events.append(a))
        with wave.open(str(root/'artifacts/asr_google'/sample['audio'])) as file:
            audio = b'\0'*8000+file.readframes(file.getnframes())+b'\0'*128000
        for i in range(0, len(audio), 4000): decoder.push(audio[i:i+4000])
        commands = [event for event in events if event[0] == 'command']
        assert len(commands) == 1, commands
        _, transcript, confidence = commands[0]
        parsed = catalog.parse(transcript)
        assert list(parsed.route) == sample['expected_route'], (sample, transcript)
        assert not parsed.route or confidence >= .65
        evidence.append(dict(audio=sample['audio'], transcript=transcript, confidence=confidence,
                             route=list(parsed.route), kind=parsed.kind, passed=True))
        print(json.dumps(evidence[-1], ensure_ascii=False), flush=True)
    (root/'artifacts/live_decoder_validation.json').write_text(json.dumps(dict(
        source='CACHED_SYNTHETIC_AUDIO', method='exact runtime make_recognizer + UtteranceDecoder PCM path',
        results=evidence), ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__': main()
