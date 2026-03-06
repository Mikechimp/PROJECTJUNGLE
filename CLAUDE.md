# CLAUDE.md - PROJECTJUNGLE

## Project Overview

PROJECTJUNGLE is an authorized vulnerability scanner for ethical cybersecurity assessments. It performs multi-phase network scanning combining port discovery, service fingerprinting, and automated vulnerability detection. Written in Python 3.8+ with **zero external dependencies** (standard library only).

- **Version:** 0.1.0 (Alpha)
- **License:** Boost Software License 1.0
- **Entry point:** `jungle=jungle.cli:main`
- **Python:** 3.8, 3.9, 3.10, 3.11, 3.12

## Repository Structure

```
PROJECTJUNGLE/
├── CLAUDE.md                  # This file
├── LICENSE                    # Boost Software License 1.0
├── README.md                  # User-facing documentation
├── SECURITY.md                # Vulnerability reporting policy
├── setup.py                   # Package setup (entry point: jungle)
├── requirements.txt           # No runtime deps; optional pytest/pytest-cov
├── .gitignore                 # Python bytecode, eggs, venvs
└── jungle/                    # Main package
    ├── __init__.py            # Package metadata (__version__, __author__)
    ├── __main__.py            # python -m jungle entry point
    ├── auth.py                # Authorization gate (CFAA compliance)
    ├── cli.py                 # CLI argument parsing and scan orchestration
    ├── config.py              # ScanConfig dataclass
    ├── scanner/               # Scanning modules
    │   ├── __init__.py
    │   ├── port_scanner.py    # TCP port scanning (ThreadPoolExecutor)
    │   ├── service_detector.py# Banner grabbing and service fingerprinting
    │   ├── network.py         # Network vulnerability checks (CVE matching, SSL)
    │   └── web.py             # Web vulnerability checks (headers, paths, certs)
    ├── report/                # Report generation
    │   ├── __init__.py
    │   └── generator.py       # Text, JSON, and HTML report output
    ├── utils/                 # Shared utilities
    │   ├── __init__.py
    │   ├── network.py         # Low-level socket/SSL operations
    │   └── validators.py      # Target/port input validation
    └── vuln/                  # Vulnerability database
        ├── __init__.py
        └── checks.py          # CVE database (14 entries)
```

## Architecture

### Scanning Pipeline

The scanner runs four sequential phases, each building on the previous:

```
CLI (cli.py)
  │
  ├── Phase 1: Port Scanning (scanner/port_scanner.py)
  │   └── ThreadPoolExecutor → tcp_connect() per port
  │
  ├── Phase 2: Service Detection (scanner/service_detector.py)
  │   └── Banner grabbing + regex pattern matching on open ports
  │
  ├── Phase 3: Network Vuln Checks (scanner/network.py)
  │   ├── Insecure service detection (Telnet, FTP)
  │   ├── Exposed database detection (MySQL, PostgreSQL, MongoDB, Redis, etc.)
  │   ├── CVE matching against vuln/checks.py database
  │   └── SSL/TLS configuration checks
  │
  └── Phase 4: Web Vuln Checks (scanner/web.py)
      ├── HTTP security header analysis
      ├── Dangerous HTTP method detection
      ├── Sensitive path exposure (.env, .git/HEAD, phpinfo, etc.)
      └── SSL certificate validation
```

**Phase dependencies:**
- Phase 2 requires Phase 1 results (open ports)
- Phase 3 requires Phase 2 results (detected services)
- Phase 4 is independent (can run standalone with `--web-only`)

### Key Data Flow

- `ScanConfig` dataclass carries all configuration through the pipeline
- Each phase returns `List[Dict]` — open ports, services, or findings
- Findings include: port, category, severity, title, description, CVE, remediation
- `ReportGenerator` aggregates all results, sorts by severity, outputs text/JSON/HTML

### Severity Levels (ordered)

CRITICAL > HIGH > MEDIUM > LOW > INFO

## Development Commands

```bash
# Install in development mode
pip install -e .

# Run the scanner
jungle <target> [options]
python -m jungle <target> [options]

# Run tests (if test files exist)
pytest
pytest --cov=jungle

# Common CLI usage
jungle 192.168.1.100                          # Basic scan
jungle example.com -p 80,443,8080             # Specific ports
jungle target.local -p 1-65535 -t 100         # Full range, 100 threads
jungle 10.0.0.50 --web-only                   # Web checks only
jungle 10.0.0.50 --network-only               # Network checks only
jungle target -o report.json --format json     # JSON report
jungle target -o report.html --format html     # HTML report
jungle target -y                               # Skip auth prompt (scripted use)
jungle target -v --timeout 5.0                 # Verbose, longer timeout
```

## Code Conventions

### Style
- **Snake_case** for functions and variables
- **PascalCase** for classes (`PortScanner`, `NetworkVulnScanner`, `ReportGenerator`)
- **UPPER_CASE** for constants (`WELL_KNOWN_SERVICES`, `BANNER_PATTERNS`, `SEVERITY_ORDER`)
- **Leading underscore** for private methods (`_check_ssl`, `_identify_service`, `_fetch`)
- Standard library imports first, then local imports
- 4-space indentation

### Type Hints
- Used throughout: `List`, `Dict`, `Optional`, `Any` from `typing`
- Return types specified on most functions

### Docstrings
- Module-level docstrings on all files
- Class and method docstrings with Args/Returns sections

### Error Handling
- Network errors are caught silently (return `None` or empty list) — scanning must not crash on unreachable ports
- `ValueError` raised only for invalid configuration (port ranges)
- Authorization gate handles `EOFError` and `KeyboardInterrupt` gracefully

### Dependencies Policy
- **Zero external runtime dependencies.** Only Python standard library modules: `socket`, `ssl`, `concurrent.futures`, `argparse`, `json`, `re`, `ipaddress`, `urllib`, `dataclasses`, `datetime`, `html`, `sys`
- Do not add external packages without strong justification
- Dev dependencies (optional): `pytest>=7.0`, `pytest-cov>=4.0`

## Key Design Decisions

### Authorization Gate
Every scan requires explicit "YES" confirmation (or `-y` flag). This is a legal safeguard against accidental unauthorized scanning (CFAA compliance). The gate is in `auth.py` and is mandatory — do not bypass or weaken it.

### Thread-Based Parallelism
Port scanning and service detection use `concurrent.futures.ThreadPoolExecutor` (default 50 threads). This is appropriate for I/O-bound socket operations. Thread count is configurable via `-t`.

### CVE Database
Known vulnerabilities are stored as a static list in `vuln/checks.py` (14 CVE entries). Version matching supports exact match, `<version`, and `<=version` comparisons. New CVEs should follow the existing dict structure with fields: `product`, `affected_versions`, `severity`, `title`, `cve`, `description`, `remediation`.

### Report Generation
`ReportGenerator` supports three formats:
- **text** — human-readable console output with severity badges
- **json** — structured data with meta, target, summary, ports, services, findings
- **html** — dark-themed HTML5 document with color-coded severity badges

## Important Constraints for AI Assistants

1. **Security tool** — This is a vulnerability scanner. All changes must preserve the authorization gate and legal compliance. Never remove or weaken security checks.
2. **Ethical use only** — Code must only support authorized security testing. Do not add features for unauthorized scanning, detection evasion, or destructive attacks.
3. **Zero-dependency philosophy** — Do not introduce external runtime packages. Use only the Python standard library.
4. **No tests yet** — The project has pytest listed as an optional dev dependency but no test directory or test files exist. When adding tests, use `pytest` and follow standard Python test conventions.
5. **Python 3.8 compatibility** — Do not use syntax or features requiring Python 3.9+ (e.g., `dict | dict` merge, `match/case`, `str.removeprefix`). Use `typing.List`, `typing.Dict`, etc. instead of built-in generics.
6. **Findings structure** — All vulnerability findings must include: `port`, `category`, `severity`, `title`, `description`, and `remediation`. The `cve` field is optional.
7. **Graceful failure** — Network operations must never crash the scanner. Catch socket/SSL/URL errors and continue scanning remaining targets.
