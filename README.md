# PROJECTJUNGLE

An authorized vulnerability scanner for ethical cybersecurity operations. Combines multi-phase scanning with automated vulnerability detection and reporting — built entirely on the Python standard library with zero external dependencies.

> **This tool is strictly for use in authorized, lawful security testing environments.** See [Legal Considerations](#legal-considerations) below.

---

## Features

- **Port Scanning** — Concurrent TCP port scanning using thread pools. Supports individual ports, comma-separated lists, and ranges (e.g. `80,443` or `1-65535`). Configurable thread count for performance tuning.
- **Service Detection** — Banner grabbing and fingerprinting for 21+ common services (HTTP, SSH, FTP, SMTP, DNS, MySQL, PostgreSQL, Redis, MongoDB, and more). Extracts product names and version numbers from banners.
- **Network Vulnerability Checks** — Detects insecure services (Telnet, FTP), exposed databases, deprecated SSL/TLS protocols, weak ciphers, and matches against 14 known CVEs including OpenSSH regreSSHion (CVE-2024-6387), Apache path traversal (CVE-2021-41773), nginx HTTP/2 Rapid Reset (CVE-2023-44487), and others.
- **Web Vulnerability Checks** — Analyzes HTTP security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection), detects dangerous HTTP methods (PUT, DELETE, TRACE), discovers exposed paths (`.env`, `.git/HEAD`, `phpinfo.php`, `/admin`, `wp-login.php`, `server-status`), and flags information disclosure via Server/X-Powered-By headers.
- **Multi-Format Reporting** — Generate reports in plain text, JSON, or styled HTML. Findings are categorized by severity: CRITICAL, HIGH, MEDIUM, LOW, and INFO.
- **Authorization Gate** — Built-in legal prompt requiring explicit confirmation before any scan begins. Supports a `-y` flag for pre-authorized scripted use.
- **Zero Dependencies** — Uses only the Python standard library (`socket`, `ssl`, `concurrent.futures`, `urllib`, `json`, `argparse`, `ipaddress`).

---

## Installation

Requires **Python 3.8+**.

```bash
# Clone the repository
git clone https://github.com/Mikechimp/PROJECTJUNGLE.git
cd PROJECTJUNGLE

# Install in development mode
pip install -e .

# Or install normally
pip install .
```

---

## Usage

After installation the `jungle` command is available:

```
jungle <target> [options]
```

You can also run it as a Python module:

```
python -m jungle <target> [options]
```

### Options

| Flag | Description | Default |
|---|---|---|
| `target` | Target host — IP address or hostname | *(required)* |
| `-p, --ports` | Ports to scan. Accepts ranges (`1-1024`) or lists (`80,443,8080`) | `1-1024` |
| `-t, --threads` | Number of concurrent scanning threads | `50` |
| `--timeout` | Connection timeout in seconds | `2.0` |
| `--skip-ports` | Skip the port scanning phase | off |
| `--web-only` | Only run web vulnerability checks | off |
| `--network-only` | Only run network vulnerability checks | off |
| `-o, --output` | Save report to file | *(none)* |
| `--format` | Report format: `text`, `json`, or `html` | `text` |
| `-v, --verbose` | Enable verbose output | off |
| `--no-banner` | Skip service banner grabbing | off |
| `-y, --yes` | Skip authorization prompt (pre-authorized) | off |
| `--version` | Show version and exit | |
| `-h, --help` | Show help and exit | |

### Examples

```bash
# Basic scan with default ports (1-1024)
jungle 192.168.1.100

# Scan specific ports
jungle example.com -p 80,443,8080

# Full port range with increased threads
jungle target.local -p 1-65535 -t 100

# Web vulnerability checks only
jungle 10.0.0.50 --web-only

# Network checks only
jungle 10.0.0.50 --network-only

# Save results as JSON
jungle 192.168.1.1 -o report.json --format json

# Generate a styled HTML report
jungle target.local -o report.html --format html

# Verbose scan with longer timeout
jungle 172.16.0.5 -v --timeout 5.0

# Non-interactive mode for scripted pipelines
jungle authorized-target.com -y -o results.json --format json
```

### Scan Phases

A full scan runs four phases in order:

1. **Port Scan** — Discovers open TCP ports on the target.
2. **Service Detection** — Grabs banners and identifies running services/versions.
3. **Network Checks** — Tests for insecure services, exposed databases, known CVEs, and SSL/TLS weaknesses.
4. **Web Checks** — Examines HTTP headers, methods, exposed paths, and certificate validity.

Use `--web-only`, `--network-only`, or `--skip-ports` to run only the phases you need.

---

## Project Structure

```
jungle/
  __init__.py           # Package metadata and version
  __main__.py           # Module entry point
  auth.py               # Authorization verification gate
  cli.py                # CLI argument parsing and scan orchestration
  config.py             # ScanConfig dataclass
  scanner/
    port_scanner.py     # TCP port scanning with concurrency
    service_detector.py # Banner grabbing and service fingerprinting
    network.py          # Network-level vulnerability checks
    web.py              # Web vulnerability checks
  report/
    generator.py        # Text, JSON, and HTML report generation
  utils/
    network.py          # Low-level network helpers (TCP, SSL, banners)
    validators.py       # IP address and hostname validation
  vuln/
    checks.py           # Known vulnerability database (14 CVEs)
```

---

## Legal Considerations

**READ THIS SECTION IN ITS ENTIRETY BEFORE USING THIS SOFTWARE.**

### Note One — Legal Responsibility & Misuse

This software, including but not limited to Project JUNGLE and any future tools developed under this repository, is created strictly for use in authorized cybersecurity research, academic training, lawful penetration testing, and professional environments where explicit written consent has been granted for security assessments. Any use outside of these contexts is strictly prohibited. This includes but is not limited to scanning, probing, exploiting, or disrupting systems, services, networks, or applications without clear and verifiable authorization from the asset owner.

Misusing this tool in any way — including scanning, probing, or interacting with systems you do not have explicit written authorization to access — is a serious federal offense. Violations of the Computer Fraud and Abuse Act (CFAA) and related cybercrime laws are classified as felonies. This is not a gray area. Unauthorized use will be treated as criminal hacking. You are subject to investigation by the Federal Bureau of Investigation (FBI), U.S. Secret Service, and other federal agencies tasked with cybersecurity enforcement.

In the United States, misuse may fall under the Computer Fraud and Abuse Act (18 U.S. Code 1030), carrying penalties of up to 10 years imprisonment for a first offense and up to 20 years for repeat violations. Civil liabilities may exceed $100,000 depending on the damages caused. Other applicable laws include the Wiretap Act (18 U.S. Code 2511), the Stored Communications Act (18 U.S. Code 2701), and individual state-level computer crime laws. International users are subject to the laws and penalties of their respective jurisdictions, which may include criminal prosecution, fines, extradition, and imprisonment.

By using, downloading, cloning, modifying, or distributing this software, you accept full responsibility for your actions. You acknowledge that misuse of this tool can result in criminal charges, civil lawsuits, job loss, certification revocation, professional sanctions, and permanent reputational damage. The author and contributors accept no liability or responsibility for how it is used. You use it at your own risk.

### Note Two — Contributions & Development

All contributions to this project are welcome only under strict professional and ethical standards. Code must be original, fully tested, and free from malicious or unintended behavior. Submissions introducing backdoors, insecure logic, or unauthorized third-party code will result in permanent bans from the project and may be reported to security, academic, or legal authorities if necessary. Every line of code will be subject to audit and rejection without warning if it fails to meet the quality and safety standards required.

The maintainer retains full authority over the project's direction, structure, scope, and who is allowed to contribute. By submitting code, you acknowledge that you are transferring rights to your contribution to the project under the terms of its license, and you grant the maintainer the right to modify, reject, or remove your submission at any time.

### Note Three — Distribution, Forking, and Enforcement

This software may be publicly viewed, forked, or cloned, but redistribution must retain all original legal warnings, disclaimers, and use restrictions without exception. Any attempt to remove or modify legal terms, present the software as safe for unrestricted use, or mask its intended purpose will be treated as a direct violation of these terms.

The author maintains full rights to enforce these terms across all public and private instances, including reporting unauthorized forks, issuing takedown notices, and taking appropriate action through GitHub's abuse system, DMCA protocols, or legal channels if necessary.
