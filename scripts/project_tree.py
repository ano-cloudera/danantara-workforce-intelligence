#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in sorted(ROOT.rglob('*')):
    if any(x in p.parts for x in ('.venv-backend','.venv-frontend','.venv-observability','.runtime')): continue
    print('  '*(len(p.relative_to(ROOT).parts)-1)+('📁 ' if p.is_dir() else '📄 ')+p.name)
