"""Import only already trusted cloud CA roots into Chromium's NSS trust database.

Run in the same execution context as the BrowserAct daemon restart. This cloud
runtime has a per-context proxy CA; a daemon started earlier can have stale trust.
Requires write access to /home/agent/.pki; request that filesystem permission if
needed. Do not change HOME, disable TLS verification, or import arbitrary roots.
"""
from pathlib import Path
import subprocess


def main():
    nss = Path('/home/agent/.pki/nssdb')
    nss.mkdir(parents=True, exist_ok=True)
    nss.chmod(0o700)
    if not (nss / 'cert9.db').exists():
        subprocess.run(['certutil', '-N', '-d', f'sql:{nss}', '--empty-password'], check=True)
    count = 0
    for cert in sorted(Path('/usr/local/share/ca-certificates').glob('*.crt')):
        verified = subprocess.run(
            ['openssl', 'verify', '-CAfile', '/etc/ssl/certs/ca-certificates.crt', str(cert)],
            capture_output=True,
        )
        if verified.returncode == 0:
            subprocess.run(['certutil', '-A', '-d', f'sql:{nss}', '-n', 'woodmood-system-' + cert.stem,
                            '-t', 'C,,', '-i', str(cert)], check=True)
            count += 1
    if not count:
        raise RuntimeError('No system-trusted cloud CA certificates found')
    print(f'Prepared Chromium trust using {count} existing system-trusted CA certificates')


if __name__ == '__main__':
    main()
