"""Known vulnerability check definitions.

Each entry defines a product, affected version range, severity, and
description. These are matched against detected service banners.
"""

NETWORK_CHECKS = [
    # OpenSSH
    {
        "product": "openssh",
        "affected_versions": ["<9.3"],
        "severity": "HIGH",
        "title": "OpenSSH pre-9.3 - Multiple Vulnerabilities",
        "cve": "CVE-2023-38408",
        "description": "{product} {version} may be vulnerable to PKCS#11-related remote code "
                       "execution via ssh-agent forwarding.",
        "remediation": "Update OpenSSH to 9.3 or later.",
    },
    {
        "product": "openssh",
        "affected_versions": ["<9.8"],
        "severity": "CRITICAL",
        "title": "OpenSSH regreSSHion (pre-9.8)",
        "cve": "CVE-2024-6387",
        "description": "{product} {version} may be vulnerable to the regreSSHion race condition "
                       "allowing unauthenticated remote code execution.",
        "remediation": "Update OpenSSH to 9.8 or later immediately.",
    },
    # Apache HTTP Server
    {
        "product": "apache",
        "affected_versions": ["<2.4.58"],
        "severity": "HIGH",
        "title": "Apache HTTP Server pre-2.4.58 - Multiple Vulnerabilities",
        "cve": "CVE-2023-45802",
        "description": "{product} {version} is vulnerable to HTTP/2 stream reset attacks "
                       "and other issues patched in 2.4.58.",
        "remediation": "Update Apache HTTP Server to 2.4.58 or later.",
    },
    {
        "product": "apache",
        "affected_versions": ["<2.4.52"],
        "severity": "CRITICAL",
        "title": "Apache HTTP Server pre-2.4.52 - Path Traversal",
        "cve": "CVE-2021-41773",
        "description": "{product} {version} is vulnerable to a path traversal vulnerability "
                       "that allows reading files outside the document root.",
        "remediation": "Update Apache HTTP Server to 2.4.52 or later.",
    },
    # nginx
    {
        "product": "nginx",
        "affected_versions": ["<1.25.3"],
        "severity": "MEDIUM",
        "title": "nginx pre-1.25.3 - HTTP/2 Rapid Reset",
        "cve": "CVE-2023-44487",
        "description": "{product} {version} may be vulnerable to the HTTP/2 Rapid Reset "
                       "denial-of-service attack.",
        "remediation": "Update nginx to 1.25.3 or later.",
    },
    # vsftpd
    {
        "product": "vsftpd",
        "affected_versions": ["2.3.4"],
        "severity": "CRITICAL",
        "title": "vsftpd 2.3.4 - Backdoor Command Execution",
        "cve": "CVE-2011-2523",
        "description": "{product} {version} contains a backdoor that allows remote command execution.",
        "remediation": "Immediately update to a clean version of vsftpd.",
    },
    # ProFTPD
    {
        "product": "proftpd",
        "affected_versions": ["<1.3.8"],
        "severity": "HIGH",
        "title": "ProFTPD pre-1.3.8 - Multiple Vulnerabilities",
        "cve": "CVE-2023-51713",
        "description": "{product} {version} may be vulnerable to out-of-bounds read in mod_sftp.",
        "remediation": "Update ProFTPD to 1.3.8 or later.",
    },
    # Redis
    {
        "product": "redis",
        "affected_versions": ["<7.0.12"],
        "severity": "HIGH",
        "title": "Redis pre-7.0.12 - Multiple Vulnerabilities",
        "cve": "CVE-2023-36824",
        "description": "{product} {version} may be vulnerable to heap overflow in COMMAND GETKEYS "
                       "and other issues.",
        "remediation": "Update Redis to 7.0.12 or later.",
    },
    # Exim
    {
        "product": "exim",
        "affected_versions": ["<4.96.1"],
        "severity": "CRITICAL",
        "title": "Exim pre-4.96.1 - Remote Code Execution",
        "cve": "CVE-2023-42115",
        "description": "{product} {version} is vulnerable to out-of-bounds write allowing "
                       "remote code execution.",
        "remediation": "Update Exim to 4.96.1 or later.",
    },
    # IIS
    {
        "product": "iis",
        "affected_versions": ["<10.0"],
        "severity": "MEDIUM",
        "title": "Outdated IIS version detected",
        "cve": "",
        "description": "{product} {version} is an older version and may be missing critical "
                       "security patches.",
        "remediation": "Update to the latest supported version of IIS with all security patches applied.",
    },
]
