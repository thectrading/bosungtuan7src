"""Compress the REAL recorded Nav2 dashboard; add clearly identified synthetic input audio.

Video timing/trajectory are unchanged. Synthetic sample playback ends at the
corresponding recorded ASR command. Original silent recording is preserved.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import wave
from zoneinfo import ZoneInfo


def main():
    import cv2
    import imageio_ffmpeg
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--artifacts', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    video, root, output = Path(args.input), Path(args.artifacts), Path(args.output)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened(): raise RuntimeError('Cannot read original video')
    frames, fps = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    duration = frames/fps
    started = datetime.strptime(video.stem.removeprefix('voice_navigation_'), '%Y%m%d_%H%M%S').replace(tzinfo=ZoneInfo('Asia/Ho_Chi_Minh')).timestamp()
    evidence = json.loads((root/'integration_results.json').read_text())
    pcm = bytearray(int(duration*16000)*2)
    schedule = []
    for command in evidence['commands']:
        path = root/'asr_google'/command['audio']
        with wave.open(str(path)) as source:
            assert source.getframerate() == 16000 and source.getnchannels() == 1 and source.getsampwidth() == 2
            data = source.readframes(source.getnframes())
        length = len(data)/32000
        start = max(0., command['wall_time']-started-length)
        offset = int(start*16000)*2
        end = min(len(pcm), offset+len(data))
        if end > offset:
            pcm[offset:end] = data[:end-offset]
        schedule.append(dict(synthetic_audio=path.name, video_start_s=start, duration_s=length))
    narration = root/'synthetic_input_audio.wav'
    with wave.open(str(narration), 'wb') as destination:
        destination.setnchannels(1); destination.setsampwidth(2); destination.setframerate(16000); destination.writeframes(pcm)
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    caption = 'INPUT AUDIO - SYNTHETIC VIETNAMESE TTS | REAL VOSK + NAV2 + GAZEBO'
    filter_arg = f"drawbox=x=16:y=753:w=1168:h=25:color=black@0.55:t=fill,drawtext=fontfile={font}:text='{caption}':x=28:y=758:fontsize=13:fontcolor=white"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'warning', '-i', str(video), '-i', str(narration),
                    '-vf', filter_arg, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart', '-shortest', str(output)], check=True)
    (root/'video_provenance.json').write_text(json.dumps(dict(original=str(video.name), output=output.name,
        video_unchanged_timing=True, original_video_frames=frames, original_fps=fps, duration_s=duration,
        audio='Synthetic Google TTS input clips added for audibility, not a human microphone recording',
        caption=caption, audio_schedule=schedule), ensure_ascii=False, indent=2)+'\n')
    print(f'Exported {output}: {duration:.1f}s, original Nav2 motion timing, labelled synthetic audio.')


if __name__ == '__main__': main()
