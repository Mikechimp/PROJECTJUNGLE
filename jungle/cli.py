"""Command-line interface for PROJECTJUNGLE vulnerability scanner."""

import argparse
import sys
import json
import os
from datetime import datetime

from jungle import __version__
from jungle.auth import require_authorization
from jungle.config import ScanConfig
from jungle.scanner.port_scanner import PortScanner
from jungle.scanner.service_detector import ServiceDetector
from jungle.scanner.network import NetworkVulnScanner
from jungle.scanner.web import WebVulnScanner
from jungle.report.generator import ReportGenerator
from jungle.utils.validators import validate_target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jungle",
        description=(
            "PROJECTJUNGLE - Authorized Vulnerability Scanner\n\n"
            "WARNING: Only use against systems you have explicit "
            "written authorization to test."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument(
        "target",
        help="Target host (IP address or hostname). Must be authorized.",
    )
    parser.add_argument(
        "-p", "--ports",
        default="1-1024",
        help="Port range to scan (default: 1-1024). Example: 80,443 or 1-65535",
    )
    parser.add_argument(
        "-t", "--threads",
        type=int,
        default=50,
        help="Number of concurrent threads (default: 50)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Connection timeout in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--skip-ports",
        action="store_true",
        help="Skip port scanning (use with --ports to specify known open ports)",
    )
    parser.add_argument(
        "--web-only",
        action="store_true",
        help="Only run web vulnerability checks",
    )
    parser.add_argument(
        "--network-only",
        action="store_true",
        help="Only run network vulnerability checks",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path for the report",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text", "html"],
        default="text",
        help="Report format (default: text)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Skip service banner grabbing",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip interactive authorization prompt (for scripted use with pre-authorized targets)",
    )

    # Advanced scanning options
    scan_group = parser.add_argument_group("advanced scanning")
    scan_group.add_argument(
        "-T", "--timing",
        type=int,
        choices=[0, 1, 2, 3, 4, 5],
        default=3,
        help=(
            "Timing profile: T0=paranoid, T1=sneaky, T2=polite, "
            "T3=normal (default), T4=aggressive, T5=insane"
        ),
    )
    scan_group.add_argument(
        "--probes",
        type=int,
        default=1,
        help="Number of probes per port for statistical consensus (default: 1)",
    )
    scan_group.add_argument(
        "--strategy",
        choices=["sequential", "random", "frequency", "entropy"],
        default="sequential",
        help=(
            "Port ordering strategy: sequential (default), random, "
            "frequency (high-probability ports first), "
            "entropy (maximally distributed ordering)"
        ),
    )
    scan_group.add_argument(
        "--max-rate",
        type=float,
        default=0.0,
        help="Maximum probes per second (default: unlimited)",
    )
    scan_group.add_argument(
        "--min-rate",
        type=float,
        default=0.0,
        help="Minimum probes per second floor (default: none)",
    )

    return parser


def print_banner():
    banner = r"""
     ██╗██╗   ██╗███╗   ██╗ ██████╗ ██╗     ███████╗
     ██║██║   ██║████╗  ██║██╔════╝ ██║     ██╔════╝
     ██║██║   ██║██╔██╗ ██║██║  ███╗██║     █████╗
██   ██║██║   ██║██║╚██╗██║██║   ██║██║     ██╔══╝
╚█████╔╝╚██████╔╝██║ ╚████║╚██████╔╝███████╗███████╗
 ╚════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚══════╝
    PROJECTJUNGLE v{version} - Authorized Vulnerability Scanner
    """.format(version=__version__)
    print(banner)


def main():
    parser = build_parser()
    args = parser.parse_args()

    print_banner()

    # Validate target
    target_info = validate_target(args.target)
    if not target_info:
        print(f"[ERROR] Invalid target: {args.target}")
        sys.exit(1)

    # Authorization gate
    if not require_authorization(args.target, skip_prompt=args.yes):
        print("[ABORTED] Authorization not confirmed. Exiting.")
        sys.exit(1)

    config = ScanConfig(
        target=target_info["resolved"],
        hostname=target_info["hostname"],
        ports=args.ports,
        threads=args.threads,
        timeout=args.timeout,
        verbose=args.verbose,
        grab_banners=not args.no_banner,
        timing_profile=args.timing,
        probes_per_port=args.probes,
        scan_strategy=args.strategy,
        max_rate=args.max_rate,
        min_rate=args.min_rate,
    )

    results = {
        "target": config.target,
        "hostname": config.hostname,
        "scan_start": datetime.utcnow().isoformat(),
        "open_ports": [],
        "services": [],
        "network_vulns": [],
        "web_vulns": [],
    }

    run_network = not args.web_only
    run_web = not args.network_only

    # Phase 1: Port scanning
    if run_network and not args.skip_ports:
        print(f"\n[*] Phase 1: Scanning ports on {config.target} ({config.hostname})")
        port_scanner = PortScanner(config)
        open_ports = port_scanner.scan()
        results["open_ports"] = open_ports
        scan_stats = port_scanner.get_scan_statistics()
        results["scan_statistics"] = scan_stats

        print(f"[+] Found {len(open_ports)} open port(s)")
        if scan_stats.get("filtered", 0) > 0:
            print(f"    ({scan_stats['filtered']} filtered)")

        if config.verbose:
            for port_info in open_ports:
                state = port_info.get("state", "open")
                conf = port_info.get("confidence", 1.0)
                rtt_info = port_info.get("rtt", {})
                rtt_str = ""
                if rtt_info:
                    rtt_str = f"  rtt={rtt_info['mean_ms']:.1f}ms"
                print(f"    {port_info['port']}/tcp  {state}  "
                      f"conf={conf:.0%}{rtt_str}")

            # Print aggregate stats
            if scan_stats.get("aggregate_rtt_mean_ms") is not None:
                print(f"\n    Aggregate RTT: "
                      f"mean={scan_stats['aggregate_rtt_mean_ms']:.1f}ms")
                if scan_stats.get("aggregate_rtt_stddev_ms") is not None:
                    print(f"                   "
                          f"stddev={scan_stats['aggregate_rtt_stddev_ms']:.1f}ms")
            if scan_stats.get("adaptive_timeout_final_ms") is not None:
                print(f"    Adaptive timeout converged to: "
                      f"{scan_stats['adaptive_timeout_final_ms']:.1f}ms")
            print(f"    Total probes sent: {scan_stats['total_probes_sent']}")
    else:
        print("\n[*] Phase 1: Port scanning skipped")

    # Phase 2: Service detection
    if run_network and results["open_ports"] and config.grab_banners:
        print(f"\n[*] Phase 2: Detecting services on open ports")
        service_detector = ServiceDetector(config)
        services = service_detector.detect(results["open_ports"])
        results["services"] = services
        print(f"[+] Identified {len(services)} service(s)")

        if config.verbose:
            for svc in services:
                print(f"    {svc['port']}/tcp  {svc['service']}  {svc.get('version', '')}")
    else:
        print("\n[*] Phase 2: Service detection skipped")

    # Phase 3: Network vulnerability checks
    if run_network and results["services"]:
        print(f"\n[*] Phase 3: Running network vulnerability checks")
        net_scanner = NetworkVulnScanner(config)
        net_vulns = net_scanner.check(results["services"])
        results["network_vulns"] = net_vulns
        print(f"[+] Found {len(net_vulns)} network finding(s)")
    else:
        if run_network:
            print("\n[*] Phase 3: No services to check for network vulnerabilities")

    # Phase 4: Web vulnerability checks
    if run_web:
        web_ports = [
            p["port"] for p in results.get("services", [])
            if p.get("service") in ("http", "https")
        ]
        # Default to checking 80/443 if no port scan was done
        if not web_ports and (args.skip_ports or args.web_only):
            web_ports = [80, 443]

        if web_ports:
            print(f"\n[*] Phase 4: Running web vulnerability checks on port(s) {web_ports}")
            web_scanner = WebVulnScanner(config)
            web_vulns = web_scanner.check(web_ports)
            results["web_vulns"] = web_vulns
            print(f"[+] Found {len(web_vulns)} web finding(s)")
        else:
            print("\n[*] Phase 4: No web services detected, skipping web checks")

    results["scan_end"] = datetime.utcnow().isoformat()

    # Generate report
    total_findings = len(results["network_vulns"]) + len(results["web_vulns"])
    print(f"\n{'='*60}")
    print(f"[*] Scan complete. Total findings: {total_findings}")

    report = ReportGenerator(results)

    if args.output:
        report.save(args.output, fmt=args.format)
        print(f"[+] Report saved to {args.output}")
    else:
        print()
        report.print_summary()


if __name__ == "__main__":
    main()
