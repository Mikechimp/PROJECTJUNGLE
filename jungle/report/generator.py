"""Report generation for scan results."""

import json
import html as html_lib
from typing import Dict, List


SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


class ReportGenerator:
    """Generate scan reports in multiple formats."""

    def __init__(self, results: Dict):
        self.results = results
        self.all_findings = sorted(
            results.get("network_vulns", []) + results.get("web_vulns", []),
            key=lambda f: SEVERITY_ORDER.get(f.get("severity", "INFO"), 5),
        )

    def print_summary(self):
        """Print a text summary to stdout."""
        print(self._generate_text())

    def save(self, path: str, fmt: str = "text"):
        """Save report to a file."""
        if fmt == "json":
            content = self._generate_json()
        elif fmt == "html":
            content = self._generate_html()
        else:
            content = self._generate_text()

        with open(path, "w") as f:
            f.write(content)

    def _generate_text(self) -> str:
        """Generate a plain text report."""
        lines = []
        r = self.results
        line = "=" * 60

        lines.append(line)
        lines.append("  PROJECTJUNGLE - Vulnerability Scan Report")
        lines.append(line)
        lines.append(f"  Target:     {r['target']} ({r.get('hostname', '')})")
        lines.append(f"  Scan Start: {r.get('scan_start', 'N/A')}")
        lines.append(f"  Scan End:   {r.get('scan_end', 'N/A')}")
        lines.append("")

        # Summary counts
        counts = self._severity_counts()
        lines.append("  SUMMARY")
        lines.append(f"  Open Ports:  {len(r.get('open_ports', []))}")
        lines.append(f"  Services:    {len(r.get('services', []))}")
        lines.append(f"  Findings:    {len(self.all_findings)}")
        lines.append(f"    Critical:  {counts.get('CRITICAL', 0)}")
        lines.append(f"    High:      {counts.get('HIGH', 0)}")
        lines.append(f"    Medium:    {counts.get('MEDIUM', 0)}")
        lines.append(f"    Low:       {counts.get('LOW', 0)}")
        lines.append(f"    Info:      {counts.get('INFO', 0)}")
        lines.append("")

        # Open ports
        if r.get("open_ports"):
            lines.append("-" * 60)
            lines.append("  OPEN PORTS")
            lines.append("-" * 60)
            for p in r["open_ports"]:
                lines.append(f"    {p['port']}/tcp  {p['state']}")
            lines.append("")

        # Services
        if r.get("services"):
            lines.append("-" * 60)
            lines.append("  DETECTED SERVICES")
            lines.append("-" * 60)
            for s in r["services"]:
                svc_str = f"    {s['port']}/tcp  {s['service']}"
                if s.get("product"):
                    svc_str += f"  ({s['product']}"
                    if s.get("version"):
                        svc_str += f" {s['version']}"
                    svc_str += ")"
                lines.append(svc_str)
            lines.append("")

        # Findings
        if self.all_findings:
            lines.append("-" * 60)
            lines.append("  FINDINGS")
            lines.append("-" * 60)
            for i, f in enumerate(self.all_findings, 1):
                lines.append(f"  [{f['severity']}] #{i}: {f['title']}")
                lines.append(f"    Port:        {f.get('port', 'N/A')}")
                lines.append(f"    Category:    {f.get('category', '')}")
                if f.get("cve"):
                    lines.append(f"    CVE:         {f['cve']}")
                lines.append(f"    Description: {f.get('description', '')}")
                if f.get("remediation"):
                    lines.append(f"    Remediation: {f['remediation']}")
                lines.append("")

        lines.append(line)
        lines.append("  End of Report")
        lines.append(line)

        return "\n".join(lines)

    def _generate_json(self) -> str:
        """Generate a JSON report."""
        report = {
            "meta": {
                "tool": "PROJECTJUNGLE",
                "version": "0.1.0",
                "scan_start": self.results.get("scan_start"),
                "scan_end": self.results.get("scan_end"),
            },
            "target": {
                "ip": self.results["target"],
                "hostname": self.results.get("hostname", ""),
            },
            "summary": {
                "open_ports": len(self.results.get("open_ports", [])),
                "services": len(self.results.get("services", [])),
                "findings": len(self.all_findings),
                "severity_counts": self._severity_counts(),
            },
            "open_ports": self.results.get("open_ports", []),
            "services": self.results.get("services", []),
            "findings": self.all_findings,
        }
        return json.dumps(report, indent=2)

    def _generate_html(self) -> str:
        """Generate an HTML report."""
        r = self.results
        counts = self._severity_counts()
        e = html_lib.escape

        findings_html = ""
        for i, f in enumerate(self.all_findings, 1):
            sev = f.get("severity", "INFO")
            sev_class = sev.lower()
            cve_row = ""
            if f.get("cve"):
                cve_row = f'<tr><td><strong>CVE</strong></td><td>{e(f["cve"])}</td></tr>'
            remediation_row = ""
            if f.get("remediation"):
                remediation_row = f'<tr><td><strong>Remediation</strong></td><td>{e(f["remediation"])}</td></tr>'

            findings_html += f"""
            <div class="finding {sev_class}">
                <h3><span class="severity-badge {sev_class}">{e(sev)}</span> #{i}: {e(f.get('title', ''))}</h3>
                <table>
                    <tr><td><strong>Port</strong></td><td>{f.get('port', 'N/A')}</td></tr>
                    <tr><td><strong>Category</strong></td><td>{e(f.get('category', ''))}</td></tr>
                    {cve_row}
                    <tr><td><strong>Description</strong></td><td>{e(f.get('description', ''))}</td></tr>
                    {remediation_row}
                </table>
            </div>
            """

        ports_html = ""
        for p in r.get("open_ports", []):
            ports_html += f"<tr><td>{p['port']}</td><td>tcp</td><td>{e(p['state'])}</td></tr>"

        services_html = ""
        for s in r.get("services", []):
            ver = f"{s.get('product', '')} {s.get('version', '')}".strip()
            services_html += f"<tr><td>{s['port']}</td><td>{e(s['service'])}</td><td>{e(ver)}</td><td>{e(s.get('banner', '')[:80])}</td></tr>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROJECTJUNGLE Scan Report - {e(r['target'])}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 2rem; }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        h1 {{ color: #00ff41; margin-bottom: 0.5rem; font-family: monospace; }}
        h2 {{ color: #00cc33; margin: 1.5rem 0 0.75rem; border-bottom: 1px solid #333; padding-bottom: 0.5rem; }}
        h3 {{ margin-bottom: 0.5rem; }}
        .meta {{ color: #888; margin-bottom: 1.5rem; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem; margin: 1rem 0; }}
        .stat {{ background: #1a1a1a; padding: 1rem; border-radius: 8px; text-align: center; border: 1px solid #333; }}
        .stat .number {{ font-size: 1.8rem; font-weight: bold; }}
        .stat .label {{ font-size: 0.85rem; color: #888; }}
        .stat.critical .number {{ color: #ff1744; }}
        .stat.high .number {{ color: #ff6d00; }}
        .stat.medium .number {{ color: #ffd600; }}
        .stat.low .number {{ color: #00b0ff; }}
        .stat.info .number {{ color: #888; }}
        table {{ width: 100%; border-collapse: collapse; margin: 0.5rem 0; }}
        th, td {{ padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #222; }}
        th {{ background: #1a1a1a; color: #00ff41; }}
        .finding {{ background: #1a1a1a; border-radius: 8px; padding: 1rem; margin: 0.75rem 0; border-left: 4px solid #333; }}
        .finding.critical {{ border-left-color: #ff1744; }}
        .finding.high {{ border-left-color: #ff6d00; }}
        .finding.medium {{ border-left-color: #ffd600; }}
        .finding.low {{ border-left-color: #00b0ff; }}
        .finding.info {{ border-left-color: #666; }}
        .severity-badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; color: #000; }}
        .severity-badge.critical {{ background: #ff1744; color: #fff; }}
        .severity-badge.high {{ background: #ff6d00; }}
        .severity-badge.medium {{ background: #ffd600; }}
        .severity-badge.low {{ background: #00b0ff; }}
        .severity-badge.info {{ background: #666; color: #fff; }}
        .footer {{ margin-top: 2rem; text-align: center; color: #555; font-size: 0.85rem; }}
    </style>
</head>
<body>
<div class="container">
    <h1>PROJECTJUNGLE</h1>
    <p class="meta">Vulnerability Scan Report</p>

    <h2>Target</h2>
    <table>
        <tr><td><strong>IP Address</strong></td><td>{e(r['target'])}</td></tr>
        <tr><td><strong>Hostname</strong></td><td>{e(r.get('hostname', ''))}</td></tr>
        <tr><td><strong>Scan Start</strong></td><td>{e(r.get('scan_start', 'N/A'))}</td></tr>
        <tr><td><strong>Scan End</strong></td><td>{e(r.get('scan_end', 'N/A'))}</td></tr>
    </table>

    <h2>Summary</h2>
    <div class="summary">
        <div class="stat"><div class="number">{len(r.get('open_ports', []))}</div><div class="label">Open Ports</div></div>
        <div class="stat"><div class="number">{len(r.get('services', []))}</div><div class="label">Services</div></div>
        <div class="stat critical"><div class="number">{counts.get('CRITICAL', 0)}</div><div class="label">Critical</div></div>
        <div class="stat high"><div class="number">{counts.get('HIGH', 0)}</div><div class="label">High</div></div>
        <div class="stat medium"><div class="number">{counts.get('MEDIUM', 0)}</div><div class="label">Medium</div></div>
        <div class="stat low"><div class="number">{counts.get('LOW', 0)}</div><div class="label">Low</div></div>
        <div class="stat info"><div class="number">{counts.get('INFO', 0)}</div><div class="label">Info</div></div>
    </div>

    <h2>Open Ports</h2>
    <table>
        <thead><tr><th>Port</th><th>Protocol</th><th>State</th></tr></thead>
        <tbody>{ports_html if ports_html else '<tr><td colspan="3">No open ports found</td></tr>'}</tbody>
    </table>

    <h2>Detected Services</h2>
    <table>
        <thead><tr><th>Port</th><th>Service</th><th>Version</th><th>Banner</th></tr></thead>
        <tbody>{services_html if services_html else '<tr><td colspan="4">No services detected</td></tr>'}</tbody>
    </table>

    <h2>Findings ({len(self.all_findings)})</h2>
    {findings_html if findings_html else '<p>No vulnerabilities found.</p>'}

    <div class="footer">
        <p>Generated by PROJECTJUNGLE v0.1.0</p>
        <p>This report is confidential. Authorized use only.</p>
    </div>
</div>
</body>
</html>"""

    def _severity_counts(self) -> Dict[str, int]:
        """Count findings by severity level."""
        counts = {}
        for f in self.all_findings:
            sev = f.get("severity", "INFO")
            counts[sev] = counts.get(sev, 0) + 1
        return counts
