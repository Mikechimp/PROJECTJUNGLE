"""Service detection and banner grabbing."""

import re
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from jungle.config import ScanConfig
from jungle.utils.network import grab_banner


# Well-known ports and their typical services
WELL_KNOWN_SERVICES = {
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    80: "http",
    110: "pop3",
    111: "rpcbind",
    135: "msrpc",
    139: "netbios-ssn",
    143: "imap",
    443: "https",
    445: "microsoft-ds",
    465: "smtps",
    587: "submission",
    993: "imaps",
    995: "pop3s",
    1433: "mssql",
    1521: "oracle",
    3306: "mysql",
    3389: "ms-wbt-server",
    5432: "postgresql",
    5900: "vnc",
    6379: "redis",
    8080: "http-proxy",
    8443: "https-alt",
    27017: "mongodb",
}

# Patterns to identify services from banners
BANNER_PATTERNS = [
    (re.compile(r"SSH-[\d.]+-OpenSSH[_\s]*([\w.]+)", re.I), "ssh", "OpenSSH"),
    (re.compile(r"SSH-[\d.]+-dropbear[_\s]*([\w.]+)", re.I), "ssh", "Dropbear"),
    (re.compile(r"220.*FTP", re.I), "ftp", None),
    (re.compile(r"220.*vsftpd\s+([\d.]+)", re.I), "ftp", "vsftpd"),
    (re.compile(r"220.*ProFTPD\s+([\d.]+)", re.I), "ftp", "ProFTPD"),
    (re.compile(r"220.*FileZilla", re.I), "ftp", "FileZilla"),
    (re.compile(r"220.*SMTP", re.I), "smtp", None),
    (re.compile(r"220.*Postfix", re.I), "smtp", "Postfix"),
    (re.compile(r"220.*Exim\s+([\d.]+)", re.I), "smtp", "Exim"),
    (re.compile(r"MySQL", re.I), "mysql", "MySQL"),
    (re.compile(r"MariaDB", re.I), "mysql", "MariaDB"),
    (re.compile(r"PostgreSQL", re.I), "postgresql", "PostgreSQL"),
    (re.compile(r"redis_version:([\d.]+)", re.I), "redis", "Redis"),
    (re.compile(r"MongoDB", re.I), "mongodb", "MongoDB"),
    (re.compile(r"Apache/([\d.]+)", re.I), "http", "Apache"),
    (re.compile(r"nginx/([\d.]+)", re.I), "http", "nginx"),
    (re.compile(r"Microsoft-IIS/([\d.]+)", re.I), "http", "IIS"),
    (re.compile(r"HTTP/\d\.\d", re.I), "http", None),
]


class ServiceDetector:
    """Detect services running on open ports via banner grabbing."""

    def __init__(self, config: ScanConfig):
        self.config = config

    def detect(self, open_ports: List[Dict]) -> List[Dict]:
        """Detect services on the given open ports.

        Args:
            open_ports: List of port dicts from PortScanner.

        Returns:
            List of service dicts with port, service, version, banner.
        """
        services = []

        with ThreadPoolExecutor(max_workers=min(self.config.threads, len(open_ports))) as executor:
            futures = {
                executor.submit(self._identify_service, p["port"]): p["port"]
                for p in open_ports
            }

            for future in as_completed(futures):
                port = futures[future]
                try:
                    result = future.result()
                    if result:
                        services.append(result)
                except Exception:
                    services.append({
                        "port": port,
                        "service": WELL_KNOWN_SERVICES.get(port, "unknown"),
                        "version": "",
                        "banner": "",
                    })

        return sorted(services, key=lambda s: s["port"])

    def _identify_service(self, port: int) -> Dict:
        """Identify the service on a single port."""
        banner = grab_banner(self.config.target, port, self.config.timeout)
        service_name = WELL_KNOWN_SERVICES.get(port, "unknown")
        version = ""
        product = ""

        if banner:
            for pattern, svc, prod in BANNER_PATTERNS:
                match = pattern.search(banner)
                if match:
                    service_name = svc
                    product = prod or ""
                    if match.lastindex and match.lastindex >= 1:
                        version = match.group(1)
                    break

        return {
            "port": port,
            "service": service_name,
            "product": product,
            "version": version,
            "banner": (banner or "")[:200],  # Truncate long banners
        }
