"""Optional: create generic Vietnamese Google TTS test sentences, then decode with Vosk.

Only sample sentences are sent for TTS. Never used for microphone recognition.
Cached WAV files allow all subsequent tests to run offline.
"""
import argparse
import json
from pathlib import Path
import subprocess
import wave

from synthetic_speech import recognize
from turtlebot4_voice_nav.commands import RegionCatalog
from turtlebot4_voice_nav.speech import MODEL_PATH, GRAMMAR


def main():
    from gtts import gTTS
    import imageio_ffmpeg
    from vosk import Model, SetLogLevel
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True); parser.add_argument('--regions', required=True)
    args = parser.parse_args()
    root = Path(args.output); root.mkdir(parents=True, exist_ok=True)
    catalog = RegionCatalog(args.regions)
    SetLogLevel(-1)
    model, rows = Model(str(MODEL_PATH)), []
    cases = [('Đi đến khu vực A', ['A']), ('Di chuyển từ khu vực A đến khu vực B', ['A', 'B']),
             ('Đi đến phòng thí nghiệm', ['B']), ('Đi đến hành lang', ['C']), ('Đi đến khu vực D', [])]
    for i, (phrase, expected) in enumerate(cases, 1):
        mp3, wav = root/f'command_{i}.mp3', root/f'command_{i}.wav'
        if not mp3.exists():
            gTTS(phrase, lang='vi', timeout=20).save(str(mp3))
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', str(mp3),
                        '-ar', '16000', '-ac', '1', str(wav)], check=True)
        with wave.open(str(wav)) as file:
            pcm = b'\0'*8000+file.readframes(file.getnframes())+b'\0'*32000
        text, confidence = recognize(model, pcm, GRAMMAR)
        parsed = catalog.parse(text)
        row = dict(source='SYNTHETIC_GOOGLE_TTS_AUDIO', audio=wav.name, spoken=phrase, transcript=text,
                   confidence=confidence, kind=parsed.kind, route=list(parsed.route), expected_route=expected,
                   passed=list(parsed.route) == expected and (not expected or confidence >= .65))
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    (root/'asr_results.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
    if not all(row['passed'] for row in rows): raise SystemExit(1)


if __name__ == '__main__': main()
