"""Advanced TCP port scanner with statistical analysis and adaptive timing.

Provides multi-probe scanning with:
- Configurable timing profiles and adaptive timeouts (RFC 6298 EWMA)
- Port ordering strategies (sequential, random, frequency-weighted, entropy)
- Multi-probe consensus with confidence scoring
- RTT statistical analysis per port and aggregate
- Port state differentiation (open / closed / filtered)
- Adaptive parallelism with congestion-aware backoff
- Rate-limited scanning with token bucket algorithm
"""

import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from jungle.config import ScanConfig
from jungle.utils.network import tcp_probe, ProbeResult
from jungle.scanner.timing import (
    TimingEngine, TimingProfile, TimingParams, TIMING_PRESETS,
)
from jungle.scanner.strategies import apply_strategy


@dataclass
class PortStatistics:
    """Statistical summary of probe results for a single port.

    Computed from N probes to give a mathematically grounded
    assessment of port state with confidence scoring.
    """
    port: int
    state: str                         # Consensus state: open/closed/filtered
    confidence: float                  # 0.0 - 1.0
    probes_sent: int = 0
    probes_open: int = 0
    probes_closed: int = 0
    probes_filtered: int = 0
    rtt_min: Optional[float] = None    # Minimum RTT (seconds)
    rtt_max: Optional[float] = None    # Maximum RTT (seconds)
    rtt_mean: Optional[float] = None   # Arithmetic mean RTT
    rtt_stddev: Optional[float] = None # Standard deviation of RTT
    rtt_median: Optional[float] = None # Median RTT

    def to_dict(self) -> Dict:
        """Convert to a serializable dictionary."""
        d = {
            "port": self.port,
            "protocol": "tcp",
            "state": self.state,
            "confidence": round(self.confidence, 3),
            "probes": {
                "sent": self.probes_sent,
                "open": self.probes_open,
                "closed": self.probes_closed,
                "filtered": self.probes_filtered,
            },
        }
        if self.rtt_mean is not None:
            d["rtt"] = {
                "min_ms": round(self.rtt_min * 1000, 2),
                "max_ms": round(self.rtt_max * 1000, 2),
                "mean_ms": round(self.rtt_mean * 1000, 2),
                "stddev_ms": round(self.rtt_stddev * 1000, 2) if self.rtt_stddev else 0.0,
                "median_ms": round(self.rtt_median * 1000, 2),
            }
        return d


@dataclass
class ScanStatistics:
    """Aggregate statistics across the entire scan."""
    total_ports: int = 0
    open_ports: int = 0
    closed_ports: int = 0
    filtered_ports: int = 0
    total_probes: int = 0
    aggregate_rtt_mean: Optional[float] = None
    aggregate_rtt_stddev: Optional[float] = None
    adaptive_timeout_final: Optional[float] = None
    timing_profile: str = ""
    strategy: str = ""

    def to_dict(self) -> Dict:
        d = {
            "total_ports_scanned": self.total_ports,
            "open": self.open_ports,
            "closed": self.closed_ports,
            "filtered": self.filtered_ports,
            "total_probes_sent": self.total_probes,
            "timing_profile": self.timing_profile,
            "strategy": self.strategy,
        }
        if self.aggregate_rtt_mean is not None:
            d["aggregate_rtt_mean_ms"] = round(self.aggregate_rtt_mean * 1000, 2)
        if self.aggregate_rtt_stddev is not None:
            d["aggregate_rtt_stddev_ms"] = round(self.aggregate_rtt_stddev * 1000, 2)
        if self.adaptive_timeout_final is not None:
            d["adaptive_timeout_final_ms"] = round(self.adaptive_timeout_final * 1000, 2)
        return d


def _compute_rtt_stats(rtt_samples: List[float]):
    """Compute statistical summary of RTT samples.

    Returns (min, max, mean, stddev, median) or all None if no samples.
    """
    if not rtt_samples:
        return None, None, None, None, None

    n = len(rtt_samples)
    rtt_min = min(rtt_samples)
    rtt_max = max(rtt_samples)
    rtt_mean = sum(rtt_samples) / n

    if n >= 2:
        variance = sum((x - rtt_mean) ** 2 for x in rtt_samples) / (n - 1)
        rtt_stddev = math.sqrt(variance)
    else:
        rtt_stddev = 0.0

    sorted_rtt = sorted(rtt_samples)
    if n % 2 == 1:
        rtt_median = sorted_rtt[n // 2]
    else:
        rtt_median = (sorted_rtt[n // 2 - 1] + sorted_rtt[n // 2]) / 2.0

    return rtt_min, rtt_max, rtt_mean, rtt_stddev, rtt_median


def _consensus_state(results: List[ProbeResult]) -> tuple:
    """Determine port state by majority vote across probes.

    Returns (state, confidence) where confidence is the fraction
    of probes agreeing with the consensus.

    Tie-breaking priority: open > filtered > closed
    (if a port is ever open, that's the most useful signal)
    """
    counts = {"open": 0, "closed": 0, "filtered": 0}
    for r in results:
        counts[r.state] += 1

    total = len(results)

    # If any probe got "open", that's a strong signal
    if counts["open"] > 0:
        # Confidence is weighted: open responses / total, but boosted
        # because even one open response is highly indicative
        confidence = (counts["open"] / total) * 0.8 + 0.2
        return "open", min(confidence, 1.0)

    # Between filtered and closed, go with majority
    if counts["filtered"] >= counts["closed"]:
        return "filtered", counts["filtered"] / total
    else:
        return "closed", counts["closed"] / total


class PortScanner:
    """Advanced port scanner with statistical analysis and adaptive timing.

    Replaces simple TCP connect scanning with a full recon engine:
    - Adaptive timeout via EWMA of observed RTTs
    - Configurable scan strategies for port ordering
    - Multi-probe consensus for reliable state determination
    - Per-port and aggregate statistical analysis
    - Rate limiting and congestion-aware parallelism
    """

    def __init__(self, config: ScanConfig):
        self.config = config
        self._build_timing_engine()
        self.scan_stats = ScanStatistics()

    def _build_timing_engine(self):
        """Initialize the timing engine from config parameters."""
        profile = TimingProfile(self.config.timing_profile)
        preset = TIMING_PRESETS[profile]

        # Start from the preset, then overlay user overrides
        params = TimingParams(**preset.__dict__)
        if self.config.max_rate > 0:
            params.max_rate = self.config.max_rate
        if self.config.min_rate > 0:
            params.min_rate = self.config.min_rate
        params.max_parallelism = self.config.threads
        params.initial_timeout = self.config.timeout

        self.timing = TimingEngine(params=params, profile=profile)
        self.scan_stats.timing_profile = profile.name
        self.scan_stats.strategy = self.config.scan_strategy

    def scan(self) -> List[Dict]:
        """Run the full scan and return results.

        Returns a list of dicts compatible with the existing interface,
        but enriched with state, confidence, and RTT data.
        """
        ports = self.config.parse_ports()
        ports = apply_strategy(ports, self.config.scan_strategy)
        total = len(ports)

        self.scan_stats.total_ports = total

        if self.config.verbose:
            print(f"    Scanning {total} port(s) | "
                  f"timing: T{self.config.timing_profile} | "
                  f"strategy: {self.config.scan_strategy} | "
                  f"probes: {self.config.probes_per_port}")

        port_stats = []
        all_rtt_samples = []

        with ThreadPoolExecutor(max_workers=self.config.threads) as executor:
            futures = {}
            for port in ports:
                future = executor.submit(self._probe_port, port)
                futures[future] = port

            done_count = 0
            for future in as_completed(futures):
                done_count += 1

                if not self.config.verbose and total > 100 and done_count % 200 == 0:
                    pct = int(done_count / total * 100)
                    sys.stdout.write(f"\r    Progress: {pct}%")
                    sys.stdout.flush()

                try:
                    ps = future.result()
                    port_stats.append(ps)
                    if ps.rtt_mean is not None:
                        all_rtt_samples.append(ps.rtt_mean)
                except Exception:
                    pass

        if not self.config.verbose and total > 100:
            sys.stdout.write("\r    Progress: 100%\n")
            sys.stdout.flush()

        # Compute aggregate statistics
        self._finalize_stats(port_stats, all_rtt_samples)

        # Filter and format results
        results = []
        for ps in sorted(port_stats, key=lambda p: p.port):
            if ps.state == "open":
                results.append(ps.to_dict())
            elif ps.state == "filtered" and self.config.verbose:
                results.append(ps.to_dict())

        return results

    def _probe_port(self, port: int) -> PortStatistics:
        """Probe a single port N times and compute statistics."""
        probe_results = []

        for _ in range(self.config.probes_per_port):
            self.timing.before_probe()
            timeout = self.timing.get_timeout()
            result = tcp_probe(self.config.target, port, timeout)
            probe_results.append(result)

            # Feed data back into the adaptive models
            responded = result.state in ("open", "closed")
            self.timing.after_probe(result.rtt, responded)

        # Compute consensus state
        state, confidence = _consensus_state(probe_results)

        # Compute RTT statistics from successful probes
        rtt_samples = [r.rtt for r in probe_results if r.rtt is not None]
        rtt_min, rtt_max, rtt_mean, rtt_stddev, rtt_median = _compute_rtt_stats(rtt_samples)

        return PortStatistics(
            port=port,
            state=state,
            confidence=confidence,
            probes_sent=len(probe_results),
            probes_open=sum(1 for r in probe_results if r.state == "open"),
            probes_closed=sum(1 for r in probe_results if r.state == "closed"),
            probes_filtered=sum(1 for r in probe_results if r.state == "filtered"),
            rtt_min=rtt_min,
            rtt_max=rtt_max,
            rtt_mean=rtt_mean,
            rtt_stddev=rtt_stddev,
            rtt_median=rtt_median,
        )

    def _finalize_stats(self, port_stats: List[PortStatistics],
                        all_rtt: List[float]) -> None:
        """Compute aggregate scan statistics."""
        self.scan_stats.open_ports = sum(1 for p in port_stats if p.state == "open")
        self.scan_stats.closed_ports = sum(1 for p in port_stats if p.state == "closed")
        self.scan_stats.filtered_ports = sum(1 for p in port_stats if p.state == "filtered")
        self.scan_stats.total_probes = sum(p.probes_sent for p in port_stats)
        self.scan_stats.adaptive_timeout_final = self.timing.get_timeout()

        if all_rtt:
            n = len(all_rtt)
            self.scan_stats.aggregate_rtt_mean = sum(all_rtt) / n
            if n >= 2:
                mean = self.scan_stats.aggregate_rtt_mean
                var = sum((x - mean) ** 2 for x in all_rtt) / (n - 1)
                self.scan_stats.aggregate_rtt_stddev = math.sqrt(var)

    def get_scan_statistics(self) -> Dict:
        """Return aggregate scan statistics as a dict."""
        return self.scan_stats.to_dict()
