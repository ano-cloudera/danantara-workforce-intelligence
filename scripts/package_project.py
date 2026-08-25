#!/usr/bin/env python3
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT.parent/(ROOT.name+'.zip')
skip={'.env','.DS_Store'}
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
    for p in ROOT.rglob('*'):
        if p.is_dir() or p.name in skip or p.suffix == '.pyc' or '__pycache__' in p.parts or any(part.startswith('.venv') for part in p.parts) or '.runtime' in p.parts: continue
        z.write(p,p.relative_to(ROOT.parent))
print(OUT)
