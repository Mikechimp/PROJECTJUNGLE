"""Network utility functions."""

import socket
import ssl
from typing import Optional, Dict, Any


def tcp_connect(host: str, port: int, timeout: float = 2.0) -> bool:
    """Attempt a TCP connection to host:port. Returns True if open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except (socket.timeout, OSError):
        return False


def grab_banner(host: str, port: int, timeout: float = 2.0) -> Optional[str]:
    """Attempt to grab a service banner from host:port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((host, port))
            # Send a blank line to trigger a response from some services
            sock.sendall(b"\r\n")
            banner = sock.recv(1024)
            return banner.decode("utf-8", errors="replace").strip()
    except (socket.timeout, OSError, ConnectionRefusedError):
        return None


def get_ssl_info(host: str, port: int = 443, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """Retrieve SSL/TLS certificate and connection information."""
    context = ssl.create_default_context()
    # We want to inspect the cert even if it has issues
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                cipher = ssock.cipher()
                protocol = ssock.version()

                return {
                    "cert": cert if cert else {},
                    "cipher_name": cipher[0] if cipher else "unknown",
                    "cipher_bits": cipher[2] if cipher else 0,
                    "protocol": protocol or "unknown",
                }
    except (ssl.SSLError, socket.timeout, OSError, ConnectionRefusedError):
        return None


def get_ssl_cert_info(host: str, port: int = 443, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """Get detailed certificate info using a validating context."""
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                return {
                    "subject": dict(x[0] for x in cert.get("subject", ())),
                    "issuer": dict(x[0] for x in cert.get("issuer", ())),
                    "notBefore": cert.get("notBefore", ""),
                    "notAfter": cert.get("notAfter", ""),
                    "serialNumber": cert.get("serialNumber", ""),
                    "version": cert.get("version", ""),
                    "valid": True,
                }
    except ssl.SSLCertVerificationError as e:
        return {"valid": False, "error": str(e)}
    except (socket.timeout, OSError, ConnectionRefusedError):
        return None
