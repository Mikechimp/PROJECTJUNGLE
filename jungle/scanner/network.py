"""Network-level vulnerability checks."""

from typing import List, Dict

from jungle.config import ScanConfig
from jungle.utils.network import get_ssl_info
from jungle.vuln.checks import NETWORK_CHECKS


class NetworkVulnScanner:
    """Check detected services against known vulnerability patterns."""

    def __init__(self, config: ScanConfig):
        self.config = config

    def check(self, services: List[Dict]) -> List[Dict]:
        """Run network vulnerability checks against detected services.

        Args:
            services: List of service dicts from ServiceDetector.

        Returns:
            List of finding dicts.
        """
        findings = []

        for svc in services:
            port = svc["port"]
            service_name = svc.get("service", "")
            product = svc.get("product", "")
            version = svc.get("version", "")
            banner = svc.get("banner", "")

            # Check for insecure/deprecated services
            findings.extend(self._check_insecure_services(svc))

            # Check for known vulnerable versions
            findings.extend(self._check_known_vulns(svc))

            # SSL/TLS checks on secure ports
            if service_name in ("https", "smtps", "imaps", "pop3s", "https-alt") or port in (443, 8443, 465, 993, 995):
                findings.extend(self._check_ssl(port))

        return findings

    def _check_insecure_services(self, svc: Dict) -> List[Dict]:
        """Flag inherently insecure services."""
        findings = []
        service_name = svc.get("service", "")
        port = svc["port"]

        insecure = {
            "telnet": {
                "severity": "HIGH",
                "title": "Telnet service detected",
                "description": "Telnet transmits credentials and data in plaintext. Replace with SSH.",
                "remediation": "Disable telnet and use SSH for remote access.",
            },
            "ftp": {
                "severity": "MEDIUM",
                "title": "FTP service detected",
                "description": "FTP transmits credentials in plaintext. Consider SFTP or FTPS.",
                "remediation": "Replace FTP with SFTP or FTPS. If FTP is required, enforce TLS.",
            },
        }

        if service_name in insecure:
            info = insecure[service_name]
            findings.append({
                "port": port,
                "category": "insecure_service",
                "severity": info["severity"],
                "title": info["title"],
                "description": info["description"],
                "remediation": info["remediation"],
            })

        # Check for unencrypted database ports exposed
        db_services = {"mysql", "postgresql", "mongodb", "redis", "mssql", "oracle"}
        if service_name in db_services:
            findings.append({
                "port": port,
                "category": "exposed_database",
                "severity": "HIGH",
                "title": f"Database service ({service_name}) exposed on port {port}",
                "description": f"The {service_name} database is accessible on a network port. "
                               "Databases should not be directly exposed to untrusted networks.",
                "remediation": "Restrict database access via firewall rules. Bind to localhost "
                               "or use a VPN/SSH tunnel for remote access.",
            })

        return findings

    def _check_known_vulns(self, svc: Dict) -> List[Dict]:
        """Check service version against known vulnerability database."""
        findings = []
        product = svc.get("product", "").lower()
        version = svc.get("version", "")
        port = svc["port"]

        if not product or not version:
            return findings

        for check in NETWORK_CHECKS:
            if check["product"].lower() == product:
                if self._version_in_range(version, check.get("affected_versions", [])):
                    findings.append({
                        "port": port,
                        "category": "known_vulnerability",
                        "severity": check["severity"],
                        "title": check["title"],
                        "description": check["description"].format(
                            product=product, version=version
                        ),
                        "cve": check.get("cve", ""),
                        "remediation": check.get("remediation", "Update to the latest version."),
                    })

        return findings

    def _check_ssl(self, port: int) -> List[Dict]:
        """Check SSL/TLS configuration for weaknesses."""
        findings = []
        ssl_info = get_ssl_info(self.config.target, port, self.config.timeout + 3)

        if not ssl_info:
            findings.append({
                "port": port,
                "category": "ssl_error",
                "severity": "INFO",
                "title": f"Could not retrieve SSL/TLS info on port {port}",
                "description": "SSL/TLS handshake failed or timed out.",
                "remediation": "Verify the service is using valid SSL/TLS.",
            })
            return findings

        protocol = ssl_info.get("protocol", "")
        cipher_bits = ssl_info.get("cipher_bits", 0)
        cipher_name = ssl_info.get("cipher_name", "")

        # Check for deprecated protocols
        deprecated_protocols = {"SSLv2", "SSLv3", "TLSv1", "TLSv1.0", "TLSv1.1"}
        if protocol in deprecated_protocols:
            findings.append({
                "port": port,
                "category": "ssl_deprecated_protocol",
                "severity": "HIGH",
                "title": f"Deprecated SSL/TLS protocol ({protocol}) on port {port}",
                "description": f"The server is using {protocol}, which is deprecated and vulnerable.",
                "remediation": "Upgrade to TLS 1.2 or TLS 1.3.",
            })

        # Check cipher strength
        if cipher_bits and cipher_bits < 128:
            findings.append({
                "port": port,
                "category": "ssl_weak_cipher",
                "severity": "HIGH",
                "title": f"Weak cipher ({cipher_name}, {cipher_bits}-bit) on port {port}",
                "description": f"The cipher suite {cipher_name} uses only {cipher_bits}-bit "
                               "encryption, which is considered weak.",
                "remediation": "Configure the server to use ciphers with at least 128-bit encryption.",
            })

        return findings

    @staticmethod
    def _version_in_range(version: str, affected: List[str]) -> bool:
        """Check if a version string falls within any of the affected ranges.

        Supports exact matches and less-than ranges like '<2.4.50'.
        """
        if not version or not affected:
            return False

        for spec in affected:
            spec = spec.strip()
            if spec.startswith("<"):
                boundary = spec[1:]
                if NetworkVulnScanner._compare_versions(version, boundary) < 0:
                    return True
            elif spec.startswith("<="):
                boundary = spec[2:]
                if NetworkVulnScanner._compare_versions(version, boundary) <= 0:
                    return True
            elif version == spec:
                return True

        return False

    @staticmethod
    def _compare_versions(a: str, b: str) -> int:
        """Compare two dotted version strings. Returns -1, 0, or 1."""
        def to_parts(v):
            parts = []
            for p in v.split("."):
                try:
                    parts.append(int(p))
                except ValueError:
                    parts.append(0)
            return parts

        pa, pb = to_parts(a), to_parts(b)
        # Pad to equal length
        while len(pa) < len(pb):
            pa.append(0)
        while len(pb) < len(pa):
            pb.append(0)

        for x, y in zip(pa, pb):
            if x < y:
                return -1
            if x > y:
                return 1
        return 0
