import hashlib
import importlib.util
from pathlib import Path
import zipfile


def test_pc_bundle_contains_only_sources_and_windows_line_endings(tmp_path):
    path=Path(__file__).resolve().parents[2]/'scripts/package-pc.py'
    spec=importlib.util.spec_from_file_location('pc_package',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    output=module.build(tmp_path/'pc.zip')
    with zipfile.ZipFile(output) as archive:
        names=archive.namelist()
        assert 'woodmood-social/scripts/pc/setup.cmd' in names
        assert 'woodmood-social/uv.lock' in names
        assert 'woodmood-social/.gitignore' in names
        assert not any('/var/' in n or '/.venv/' in n or '/.git/' in n or n.endswith('.env') for n in names)
        assert not any('bridge-token' in n or 'browsers.db' in n or 'remote-client.json' in n for n in names)
        setup=archive.read('woodmood-social/scripts/pc/setup.cmd')
        assert b'\r\n' in setup and setup.replace(b'\r\n',b'').find(b'\n')==-1
    assert hashlib.sha256(output.read_bytes()).hexdigest() in output.with_suffix('.zip.sha256').read_text()
