"""Reproducible SYNTHETIC Vietnamese audio for ASR tests; not human speech evidence."""
import audioop
import ctypes
import ctypes.util
import json
from pathlib import Path
import wave


class Synthesizer:
    def __init__(self):
        self.lib = ctypes.CDLL(ctypes.util.find_library('espeak-ng'))
        self.lib.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        self.rate = self.lib.espeak_Initialize(2, 0, None, 0)
        callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
        self.callback = callback_type(self.collect)
        self.lib.espeak_SetSynthCallback(self.callback)
        self.lib.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
        self.lib.espeak_Synth.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_int,
                                         ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        self.lib.espeak_SetParameter(1, 135, 0)
        if self.lib.espeak_SetVoiceByName(b'vi') != 0:
            raise RuntimeError('eSpeak Vietnamese voice unavailable')

    def collect(self, samples, count, events):
        if samples and count:
            self.parts.append(ctypes.string_at(samples, count*2))
        return 0

    def pcm(self, text):
        self.parts = []
        data = text.encode('utf-8')+b'\0'
        if self.lib.espeak_Synth(data, len(data), 0, 1, 0, 1, None, None) != 0:
            raise RuntimeError('Speech synthesis failed')
        self.lib.espeak_Synchronize()
        pcm, _ = audioop.ratecv(b''.join(self.parts), 2, 1, self.rate, 16000, None)
        return b'\0'*8000+pcm+b'\0'*32000


def recognize(model, pcm, grammar):
    from vosk import KaldiRecognizer
    recognizer = KaldiRecognizer(model, 16000, json.dumps(grammar, ensure_ascii=False))
    recognizer.SetWords(True)
    results = []
    for i in range(0, len(pcm), 4000):
        if recognizer.AcceptWaveform(pcm[i:i+4000]):
            results.append(json.loads(recognizer.Result()))
    results.append(json.loads(recognizer.FinalResult()))
    text = ' '.join(r.get('text', '') for r in results).strip()
    scores = [w['conf'] for r in results for w in r.get('result', []) if w.get('word') != '[unk]']
    return text, sum(scores)/len(scores) if scores else 0.


def generate(output, regions):
    from vosk import Model, SetLogLevel
    from turtlebot4_voice_nav.commands import RegionCatalog
    from turtlebot4_voice_nav.speech import MODEL_PATH, GRAMMAR
    SetLogLevel(-1)
    catalog, synth, model = RegionCatalog(regions), Synthesizer(), Model(str(MODEL_PATH))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    cases = [
        ('đi đến khu vực a', ['A']),
        ('di chuyển từ khu vực a đến khu vực bê', ['A', 'B']),
        ('đi đến phòng thí nghiệm', ['B']),
        ('đi đến hành lang', ['C']),
        ('đi đến khu vực z', []),
    ]
    evidence = []
    for i, (phrase, expected) in enumerate(cases, 1):
        pcm = synth.pcm(phrase)
        path = output/f'command_{i}.wav'
        with wave.open(str(path), 'wb') as file:
            file.setnchannels(1); file.setsampwidth(2); file.setframerate(16000); file.writeframes(pcm)
        text, confidence = recognize(model, pcm, GRAMMAR)
        parsed = catalog.parse(text)
        row = dict(source='SYNTHETIC_ESPEAK_AUDIO', audio=path.name, spoken=phrase,
                   transcript=text, confidence=confidence, kind=parsed.kind, route=list(parsed.route),
                   expected_route=expected, passed=list(parsed.route) == expected and (not expected or confidence >= .65))
        evidence.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    (output/'asr_results.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n')
    return evidence


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True); parser.add_argument('--regions', required=True)
    args = parser.parse_args()
    rows = generate(args.output, args.regions)
    if not all(r['passed'] for r in rows):
        raise SystemExit(1)
