"""Local ownership checks that do not depend on HTTP or firewall/proxy response times."""
import socket


def port_available(port):
    """A successful exclusive bind proves no bridge is listening on this IPv4 port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind(('127.0.0.1', port))
        return True
    except OSError:
        # Occupied and policy-reserved ports are both inconclusive: fail closed.
        return False


def control_browser_may_be_open(config):
    """An old CDP port marker plus an occupied port must not be treated as stopped."""
    try:
        port = int((config.profile / 'DevToolsActivePort').read_text().splitlines()[0])
    except (OSError, ValueError, IndexError):
        return False
    return 1024 <= port <= 65535 and not port_available(port)


def require_manual_access(config):
    if not port_available(config.port):
        raise SystemExit('The bridge port is in use or reserved. Stop start-bridge.cmd with Ctrl+C, then retry owner-browser.cmd. No browser was opened.')
    if control_browser_may_be_open(config):
        raise SystemExit('The Woodmood control browser may still be open. Close its window before running owner-browser.cmd. No profile files were changed.')
