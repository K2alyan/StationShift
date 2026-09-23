"""Download the original UCI archive once; verify pins on every subsequent run."""
from pathlib import Path
import hashlib
import io
import json
import urllib.request
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://archive.ics.uci.edu/static/public/501/beijing+multi+site+air+quality+data.zip'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    raw = ROOT / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    pin = ROOT / 'data/manifest.json'
    archive = raw / 'uci-501.zip'
    old = json.loads(pin.read_text()) if pin.exists() else None
    if not archive.exists():
        with urllib.request.urlopen(URL, timeout=120) as response:
            archive.write_bytes(response.read())
    content = archive.read_bytes()
    if old and old['archive_sha256'] != sha(content):
        raise ValueError('UCI archive does not match pinned SHA256')
    files = {}
    def extract(blob):
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            for name in z.namelist():
                if name.endswith('.zip'):
                    extract(z.read(name))
                elif Path(name).name.startswith('PRSA_Data_') and name.endswith('.csv'):
                    data = z.read(name)
                    filename = Path(name).name
                    files[filename] = sha(data)
                    (raw / filename).write_bytes(data)
    extract(content)
    assert len(files) == 12, files
    manifest = dict(source_url=URL, retrieved_utc=datetime.now(timezone.utc).isoformat(),
                    archive_sha256=sha(content), extracted_sha256=files)
    if old:
        assert files == old['extracted_sha256'], 'Extracted file hashes changed'
    else:
        pin.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(old or manifest, indent=2))

if __name__ == '__main__':
    main()
