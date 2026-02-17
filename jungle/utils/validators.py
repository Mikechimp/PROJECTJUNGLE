"""Input validation utilities."""

import ipaddress
import re
import socket
from typing import Optional, Dict


_HOSTNAME_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$"
)


def validate_target(target: str) -> Optional[Dict[str, str]]:
    """Validate and resolve a scan target.

    Accepts an IPv4/IPv6 address or a hostname. Hostnames are resolved
    to an IP address. Returns None if the target is invalid.

    Returns:
        dict with keys 'input', 'resolved' (IP string), 'hostname'
        or None if invalid.
    """
    target = target.strip()

    # Try parsing as IP address first
    try:
        addr = ipaddress.ip_address(target)
        if addr.is_loopback:
            # Allow localhost for testing
            pass
        return {
            "input": target,
            "resolved": str(addr),
            "hostname": target,
        }
    except ValueError:
        pass

    # Try as hostname
    if not _HOSTNAME_RE.match(target):
        return None

    try:
        resolved_ip = socket.gethostbyname(target)
        return {
            "input": target,
            "resolved": resolved_ip,
            "hostname": target,
        }
    except socket.gaierror:
        return None


def parse_port_list(port_str: str):
    """Parse a port specification string into a sorted list of ints.

    Supports individual ports (80,443) and ranges (1-1024).
    """
    ports = []
    for part in port_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            ports.extend(range(int(start), int(end) + 1))
        else:
            ports.append(int(part))
    return sorted(set(p for p in ports if 1 <= p <= 65535))
