"""Snapshot the active dependency closure, excluding unrelated host packages."""
from pathlib import Path
from importlib.metadata import distribution
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

root=Path(__file__).resolve().parents[1]
pending=[Requirement(s).name for s in (root/'requirements.txt').read_text().splitlines() if s]
seen={}
while pending:
    name=pending.pop()
    if canonicalize_name(name) in seen:
        continue
    dist=distribution(name)
    seen[canonicalize_name(name)]=f'{dist.metadata["Name"]}=={dist.version}'
    for text in dist.requires or []:
        req=Requirement(text)
        if req.marker is None or req.marker.evaluate():
            pending.append(req.name)
(root/'environment-freeze.txt').write_text('\n'.join(sorted(seen.values(),key=str.lower))+'\n')
print('Pinned',len(seen),'active packages')
