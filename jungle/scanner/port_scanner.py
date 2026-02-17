"""TCP port scanner with concurrent thread pool."""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

from jungle.config import ScanConfig
from jungle.utils.network import tcp_connect


class PortScanner:
    """Scans a target host for open TCP ports."""

    def __init__(self, config: ScanConfig):
        self.config = config

    def scan(self) -> List[Dict]:
        """Scan configured ports and return list of open port dicts."""
        ports = self.config.parse_ports()
        open_ports = []
        total = len(ports)

        if self.config.verbose:
            print(f"    Scanning {total} port(s) with {self.config.threads} threads")

        with ThreadPoolExecutor(max_workers=self.config.threads) as executor:
            futures = {
                executor.submit(
                    tcp_connect, self.config.target, port, self.config.timeout
                ): port
                for port in ports
            }

            done_count = 0
            for future in as_completed(futures):
                port = futures[future]
                done_count += 1

                if not self.config.verbose and total > 100 and done_count % 200 == 0:
                    pct = int(done_count / total * 100)
                    sys.stdout.write(f"\r    Progress: {pct}%")
                    sys.stdout.flush()

                try:
                    if future.result():
                        open_ports.append({"port": port, "protocol": "tcp", "state": "open"})
                except Exception:
                    pass

        if not self.config.verbose and total > 100:
            sys.stdout.write("\r    Progress: 100%\n")
            sys.stdout.flush()

        return sorted(open_ports, key=lambda p: p["port"])
