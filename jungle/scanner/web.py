"""Web application vulnerability checks."""

import socket
import ssl
from typing import List, Dict
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from jungle.config import ScanConfig
from jungle.utils.network import get_ssl_cert_info


class WebVulnScanner:
    """Scan web services for common misconfigurations and vulnerabilities."""

    def __init__(self, config: ScanConfig):
        self.config = config

    def check(self, web_ports: List[int]) -> List[Dict]:
        """Run web vulnerability checks against the given ports.

        Args:
            web_ports: List of port numbers with web services.

        Returns:
            List of finding dicts.
        """
        findings = []

        for port in web_ports:
            scheme = "https" if port in (443, 8443) else "http"
            base_url = f"{scheme}://{self.config.hostname}:{port}"

            findings.extend(self._check_http_headers(base_url, port))
            findings.extend(self._check_http_methods(base_url, port))
            findings.extend(self._check_common_paths(base_url, port))

            if scheme == "https":
                findings.extend(self._check_certificate(port))

        return findings

    def _fetch(self, url: str, method: str = "GET", timeout: float = 5.0):
        """Make an HTTP request and return (status_code, headers, body_snippet)."""
        # Create a context that doesn't verify SSL for scanning purposes
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            req = Request(url, method=method)
            req.add_header("User-Agent", "PROJECTJUNGLE-Scanner/0.1 (Authorized Security Assessment)")
            with urlopen(req, timeout=timeout, context=ctx) as resp:
                headers = dict(resp.headers)
                body = resp.read(4096).decode("utf-8", errors="replace")
                return resp.status, headers, body
        except HTTPError as e:
            headers = dict(e.headers) if e.headers else {}
            return e.code, headers, ""
        except (URLError, socket.timeout, OSError):
            return None, {}, ""

    def _check_http_headers(self, base_url: str, port: int) -> List[Dict]:
        """Check for missing or misconfigured security headers."""
        findings = []
        status, headers, body = self._fetch(base_url)

        if status is None:
            findings.append({
                "port": port,
                "category": "web_connectivity",
                "severity": "INFO",
                "title": f"Could not connect to web service on port {port}",
                "description": "HTTP request failed. The service may not be HTTP-based.",
                "remediation": "Verify the service type.",
            })
            return findings

        # Normalize header keys to lowercase
        h = {k.lower(): v for k, v in headers.items()}

        # Security headers to check
        security_headers = [
            {
                "header": "strict-transport-security",
                "title": "Missing HSTS header",
                "severity": "MEDIUM",
                "description": "The HTTP Strict-Transport-Security header is not set. "
                               "This allows downgrade attacks and cookie hijacking.",
                "remediation": "Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains' header.",
                "https_only": True,
            },
            {
                "header": "x-content-type-options",
                "title": "Missing X-Content-Type-Options header",
                "severity": "LOW",
                "description": "The X-Content-Type-Options header is not set to 'nosniff'. "
                               "This can lead to MIME-type confusion attacks.",
                "remediation": "Add 'X-Content-Type-Options: nosniff' header.",
                "https_only": False,
            },
            {
                "header": "x-frame-options",
                "title": "Missing X-Frame-Options header",
                "severity": "MEDIUM",
                "description": "The X-Frame-Options header is missing, which may allow "
                               "clickjacking attacks.",
                "remediation": "Add 'X-Frame-Options: DENY' or 'X-Frame-Options: SAMEORIGIN' header.",
                "https_only": False,
            },
            {
                "header": "content-security-policy",
                "title": "Missing Content-Security-Policy header",
                "severity": "MEDIUM",
                "description": "No Content-Security-Policy header detected. CSP helps prevent "
                               "XSS, clickjacking, and other code injection attacks.",
                "remediation": "Implement a Content-Security-Policy header appropriate for your application.",
                "https_only": False,
            },
            {
                "header": "x-xss-protection",
                "title": "Missing X-XSS-Protection header",
                "severity": "LOW",
                "description": "The X-XSS-Protection header is not set. While deprecated in "
                               "modern browsers, it still provides protection for older browsers.",
                "remediation": "Add 'X-XSS-Protection: 1; mode=block' header.",
                "https_only": False,
            },
        ]

        is_https = base_url.startswith("https")

        for check in security_headers:
            if check["https_only"] and not is_https:
                continue
            if check["header"] not in h:
                findings.append({
                    "port": port,
                    "category": "missing_security_header",
                    "severity": check["severity"],
                    "title": check["title"],
                    "description": check["description"],
                    "remediation": check["remediation"],
                })

        # Check for server version disclosure
        server = h.get("server", "")
        if server and ("/" in server):
            findings.append({
                "port": port,
                "category": "info_disclosure",
                "severity": "LOW",
                "title": "Server version disclosed in headers",
                "description": f"The 'Server' header reveals: {server}. "
                               "Version information aids attackers in finding known vulnerabilities.",
                "remediation": "Configure the web server to suppress version information in the Server header.",
            })

        # Check for X-Powered-By disclosure
        powered_by = h.get("x-powered-by", "")
        if powered_by:
            findings.append({
                "port": port,
                "category": "info_disclosure",
                "severity": "LOW",
                "title": "Technology stack disclosed via X-Powered-By header",
                "description": f"The 'X-Powered-By' header reveals: {powered_by}.",
                "remediation": "Remove the X-Powered-By header from server responses.",
            })

        return findings

    def _check_http_methods(self, base_url: str, port: int) -> List[Dict]:
        """Check for dangerous HTTP methods."""
        findings = []
        status, headers, _ = self._fetch(base_url, method="OPTIONS")

        if status is None:
            return findings

        h = {k.lower(): v for k, v in headers.items()}
        allow = h.get("allow", "") or h.get("access-control-allow-methods", "")

        dangerous_methods = {"PUT", "DELETE", "TRACE", "CONNECT"}
        if allow:
            methods = {m.strip().upper() for m in allow.split(",")}
            found_dangerous = methods & dangerous_methods
            if found_dangerous:
                findings.append({
                    "port": port,
                    "category": "dangerous_methods",
                    "severity": "MEDIUM",
                    "title": f"Potentially dangerous HTTP methods enabled: {', '.join(sorted(found_dangerous))}",
                    "description": f"The server allows {', '.join(sorted(found_dangerous))} methods "
                                   "which could be used to modify server content or leak information.",
                    "remediation": "Disable unnecessary HTTP methods. Only allow GET, POST, HEAD as needed.",
                })

        return findings

    def _check_common_paths(self, base_url: str, port: int) -> List[Dict]:
        """Check for commonly exposed sensitive paths."""
        findings = []

        sensitive_paths = [
            {"path": "/robots.txt", "title": "robots.txt found", "severity": "INFO",
             "description": "robots.txt is accessible and may reveal hidden paths."},
            {"path": "/.env", "title": "Environment file exposed", "severity": "CRITICAL",
             "description": ".env file is accessible and may contain secrets, API keys, and credentials."},
            {"path": "/.git/HEAD", "title": "Git repository exposed", "severity": "CRITICAL",
             "description": "The .git directory is accessible. Source code and secrets could be downloaded."},
            {"path": "/server-status", "title": "Apache server-status exposed", "severity": "MEDIUM",
             "description": "Apache server-status page is accessible, revealing server internals."},
            {"path": "/phpinfo.php", "title": "phpinfo() page exposed", "severity": "HIGH",
             "description": "phpinfo() page is accessible, disclosing server configuration details."},
            {"path": "/wp-login.php", "title": "WordPress login page found", "severity": "INFO",
             "description": "WordPress login page is accessible. Ensure strong credentials and 2FA."},
            {"path": "/admin", "title": "Admin panel found", "severity": "LOW",
             "description": "An admin panel was detected. Ensure it is properly secured."},
            {"path": "/.well-known/security.txt", "title": "security.txt found", "severity": "INFO",
             "description": "security.txt is present (good practice for responsible disclosure)."},
        ]

        for item in sensitive_paths:
            url = base_url + item["path"]
            status, headers, body = self._fetch(url)

            if status and 200 <= status < 400:
                # For .env and .git, verify content looks real
                if item["path"] == "/.env" and not any(k in body for k in ("=", "DB_", "API_", "SECRET")):
                    continue
                if item["path"] == "/.git/HEAD" and "ref:" not in body:
                    continue

                findings.append({
                    "port": port,
                    "category": "exposed_path",
                    "severity": item["severity"],
                    "title": item["title"],
                    "description": item["description"],
                    "url": url,
                    "remediation": f"Restrict access to {item['path']} via server configuration.",
                })

        return findings

    def _check_certificate(self, port: int) -> List[Dict]:
        """Check SSL certificate validity."""
        findings = []
        cert_info = get_ssl_cert_info(self.config.hostname, port, self.config.timeout + 3)

        if cert_info is None:
            return findings

        if not cert_info.get("valid", False):
            error = cert_info.get("error", "Unknown certificate error")
            findings.append({
                "port": port,
                "category": "ssl_certificate",
                "severity": "HIGH",
                "title": f"Invalid SSL certificate on port {port}",
                "description": f"Certificate validation failed: {error}",
                "remediation": "Install a valid SSL certificate from a trusted CA. "
                               "Consider using Let's Encrypt for free certificates.",
            })

        return findings
