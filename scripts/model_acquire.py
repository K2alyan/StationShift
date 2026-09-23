"""Resolve and pin one public checkpoint, then download only inference files."""
from pathlib import Path
import urllib.request
import json
import hashlib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
def main():
    dest = ROOT / 'models/chronos-2'
    dest.mkdir(parents=True, exist_ok=True)
    pin = ROOT / 'models/manifest.json'
    if pin.exists():
        meta = json.loads(pin.read_text())
    else:
        with urllib.request.urlopen('https://huggingface.co/api/models/amazon/chronos-2', timeout=90) as r:
            api = json.load(r)
        meta = dict(model_id='amazon/chronos-2', revision=api['sha'],
                    retrieved_utc=datetime.now(timezone.utc).isoformat(), files={})
    for name in ['config.json', 'model.safetensors']:
        file = dest / name
        if not file.exists():
            url = f"https://huggingface.co/amazon/chronos-2/resolve/{meta['revision']}/{name}"
            print('Downloading', url, flush=True)
            with urllib.request.urlopen(url, timeout=300) as r, file.with_suffix('.part').open('wb') as w:
                while chunk := r.read(1024*1024):
                    w.write(chunk)
            file.with_suffix('.part').replace(file)
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if name in meta['files']:
            assert meta['files'][name] == digest
        meta['files'][name] = digest
    pin.write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps(meta, indent=2))

if __name__ == '__main__':
    main()
