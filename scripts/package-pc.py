"""Build a source-only Windows setup archive; no credentials, browser state or logs."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SINGLE = ['pyproject.toml','uv.lock','.python-version','config.toml','accounts.toml',
          'README.md','AGENTS.md','.gitignore','.env.example','browser.toml']
FOLDERS = ['woodmood','scripts','docs','tests','.github']


def build(output=None):
    output = Path(output or ROOT / 'dist/woodmood-pc-setup.zip')
    output.parent.mkdir(parents=True, exist_ok=True)
    selected = [ROOT / name for name in SINGLE]
    for folder in FOLDERS:
        selected.extend(p for p in (ROOT / folder).rglob('*') if p.is_file()
                        and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.log'))
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(selected):
            name = 'woodmood-social/' + file.relative_to(ROOT).as_posix()
            if file.suffix.lower() in ('.cmd', '.ps1'):
                archive.writestr(name, file.read_text().replace('\r\n','\n').replace('\n','\r\n').encode())
            else:
                archive.write(file, name)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest + '  ' + output.name + '\n')
    return output


if __name__ == '__main__':
    print(build())
