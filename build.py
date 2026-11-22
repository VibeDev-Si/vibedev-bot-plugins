#!/usr/bin/env python3
# Reproducible builder for the maubot plugin packages (.mbp) in this repository.
# Copyright (C) 2026 VibeDev (https://github.com/VibeDev-Si)
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
# License for more details. You should have received a copy of the GNU Affero General Public License along with this
# program. If not, see <https://www.gnu.org/licenses/>.
"""Builds the plugin packages: python build.py [plugin directory ...]   (default: every plugin; Python 3.8+, stdlib only)

Writes dist/<plugin id>.mbp and dist/SHA256SUMS. The same sources give byte-identical packages on every platform:
entries sorted by name, stored without compression, fixed timestamp (1980-01-01 00:00), fixed permissions (0644),
Unix as the creating system. A package holds maubot.yaml, LICENSE, the modules and the extra_files named in
maubot.yaml (the layout `mbc build` produces, plus the license). .gitattributes turns off line-ending conversion, so
any checkout of a commit builds the same bytes."""
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGINS = ['reminder', 'dice']


def read_meta(text):
    """The parts of maubot.yaml the build needs (top-level scalars and lists), without a YAML library."""
    meta, key = {}, None
    for raw in text.splitlines():
        line = raw.split(' #', 1)[0].rstrip() if not raw.lstrip().startswith('#') else ''
        if not line:
            continue
        if line.startswith('- ') and key:
            meta.setdefault(key, []).append(line[2:].strip())
        elif ':' in line and not line.startswith(' '):
            key, value = (part.strip() for part in line.split(':', 1))
            if value:
                meta[key] = value
    return meta


def plugin_files(plugin_dir):
    """{name inside the package: content} for one plugin directory."""
    plugin_dir = Path(plugin_dir)
    meta = read_meta((plugin_dir / 'maubot.yaml').read_text(encoding='utf-8'))
    names = ['maubot.yaml', 'LICENSE'] + list(meta.get('extra_files', []))
    for module in meta.get('modules', []):
        if (plugin_dir / module).is_dir():
            names += [p.relative_to(plugin_dir).as_posix() for p in sorted((plugin_dir / module).rglob('*'))
                      if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
        else:
            names.append(f'{module}.py')
    files = {}
    for name in names:
        path = plugin_dir / name
        if not path.is_file():
            raise SystemExit(f'{plugin_dir.name}: {name} is missing')
        files[name] = path.read_bytes()
    return meta, files


def write_mbp(files, target):
    """Writes a reproducible package; returns its sha256."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_STORED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            zf.writestr(info, files[name])
    return hashlib.sha256(target.read_bytes()).hexdigest()


def main(argv):
    dist = ROOT / 'dist'
    sums = []
    for name in argv or PLUGINS:
        meta, files = plugin_files(ROOT / name)
        target = dist / f"{meta['id']}.mbp"
        digest = write_mbp(files, target)
        sums.append(f'{digest}  {target.name}')
        print(f"{target.relative_to(ROOT).as_posix()}  version={meta['version']}  files={len(files)}  sha256={digest}")
    if not argv:
        (dist / 'SHA256SUMS').write_text('\n'.join(sums) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1:])
