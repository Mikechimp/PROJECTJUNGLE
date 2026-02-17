"""Scan configuration."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ScanConfig:
    target: str
    hostname: str = ""
    ports: str = "1-1024"
    threads: int = 50
    timeout: float = 2.0
    verbose: bool = False
    grab_banners: bool = True

    def parse_ports(self) -> List[int]:
        """Parse port specification into a list of port numbers."""
        ports = []
        for part in self.ports.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                start, end = int(start), int(end)
                if start < 1 or end > 65535 or start > end:
                    raise ValueError(f"Invalid port range: {part}")
                ports.extend(range(start, end + 1))
            else:
                port = int(part)
                if port < 1 or port > 65535:
                    raise ValueError(f"Invalid port: {port}")
                ports.append(port)
        return sorted(set(ports))
