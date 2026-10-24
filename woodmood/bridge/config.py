from dataclasses import dataclass
import json
import os
from pathlib import Path
import secrets
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]


def default_directory():
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'WoodmoodSocial'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/WoodmoodSocial'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'woodmood-social'


def secure_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(text)


def find_chrome():
    import shutil
    if sys.platform == 'win32':
        for var in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            if os.environ.get(var):
                path = Path(os.environ[var]) / 'Google/Chrome/Application/chrome.exe'
                if path.exists():
                    return str(path)
    elif sys.platform == 'darwin':
        path = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        if path.exists():
            return str(path)
    for name in ('google-chrome-stable', 'google-chrome', 'chromium', 'chromium-browser'):
        if shutil.which(name):
            return shutil.which(name)
    return None


@dataclass
class BridgeConfig:
    directory: Path
    token: str
    port: int = 8787
    public_host: str | None = None
    executable: str | None = None
    headless: bool = False
    sandbox: bool = True
    connection_mode: str = "native"

    def __post_init__(self):
        self.directory = Path(self.directory).expanduser().resolve()
        if self.directory == ROOT or ROOT in self.directory.parents:
            raise ValueError('Browser state must live outside the Git checkout')
        if self.connection_mode not in ("native", "playwright"):
            raise ValueError("connection_mode must be native or playwright")
        if len(self.token) < 32:
            raise ValueError('Bridge token must contain at least 32 characters')
        if not 1024 <= self.port <= 65535:
            raise ValueError('Port must be between 1024 and 65535')
        if self.public_host:
            import re
            if not re.fullmatch(r'[a-zA-Z0-9.-]+', self.public_host) or '.' not in self.public_host:
                raise ValueError('public_host must be a hostname without scheme, path or port')
            self.public_host = self.public_host.lower()

    @property
    def paused_file(self):
        return self.directory / 'owner-control'

    @property
    def profile(self):
        return self.directory / 'chrome-profile'

    @classmethod
    def load(cls, directory=None):
        directory = Path(directory or os.environ.get('WOODMOOD_BRIDGE_DIR', default_directory())).expanduser().resolve()
        with (directory / 'bridge.json').open(encoding='utf-8') as stream:
            settings = json.load(stream)
        token_path = directory / 'bridge-token'
        if os.name != 'nt' and stat.S_IMODE(token_path.stat().st_mode) & 0o077:
            raise ValueError('bridge-token must only be readable by its owner (chmod 600)')
        return cls(directory=directory, token=token_path.read_text().strip(), **settings)


def initialize(directory=None):
    directory = Path(directory or os.environ.get('WOODMOOD_BRIDGE_DIR', default_directory())).expanduser().resolve()
    if directory == ROOT or ROOT in directory.parents:
        raise ValueError('Choose a state directory outside the Git checkout')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != 'nt':
        directory.chmod(0o700)
    # Existing credentials and owner settings are never overwritten by setup.
    token = directory / 'bridge-token'
    if not token.exists():
        secure_write(token, secrets.token_urlsafe(48))
    config = directory / 'bridge.json'
    if not config.exists():
        secure_write(config, json.dumps({'port': 8787, 'public_host': None,
                                        'executable': find_chrome(), 'headless': False,
                                        'sandbox': True, 'connection_mode': 'native'}, indent=2))
    marker = directory / 'initialized'
    if not marker.exists():
        # The first session belongs to the owner until they explicitly release it.
        (directory / 'owner-control').touch(mode=0o600, exist_ok=True)
        secure_write(marker, 'initialized\n')
    BridgeConfig.load(directory)
    return directory
