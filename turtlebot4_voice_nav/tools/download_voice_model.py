"""Download the official Vietnamese Vosk small model once; no audio is uploaded."""
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile


def main():
    root = Path.home()/'.cache/bai01_hri'
    name = 'vosk-model-small-vn-0.4'
    if (root/name/'am/final.mdl').exists():
        print('Model already installed:', root/name); return
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        archive = Path(tmp)/'model.zip'
        with urllib.request.urlopen(f'https://alphacephei.com/vosk/models/{name}.zip', timeout=60) as response:
            with archive.open('wb') as output: shutil.copyfileobj(response, output)
        with zipfile.ZipFile(archive) as package:
            for item in package.infolist():
                if not (Path(tmp)/item.filename).resolve().is_relative_to(Path(tmp).resolve()):
                    raise ValueError('Invalid model archive path')
            package.extractall(tmp)
        (Path(tmp)/name).rename(root/name)
    print('Model installed:', root/name)


if __name__ == '__main__': main()
