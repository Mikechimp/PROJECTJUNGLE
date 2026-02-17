"""Port ordering strategies for tactical scan control.

Provides different mathematical approaches to port ordering:
- Sequential: Standard ordered scan (default)
- Random: Shuffled ordering to avoid sequential pattern detection
- Frequency-weighted: Prioritize ports most likely to be open based on
  empirical service frequency distributions from large-scale internet surveys
"""

import random
import math
from typing import List


# Empirical port frequency weights based on internet-wide scan data.
# Higher weight = more commonly open in the wild.
# Ports not in this table get a baseline weight of 1.0.
# Values are approximate relative frequencies (not raw counts).
PORT_FREQUENCY = {
    80: 100.0,    # HTTP — most commonly open port on the internet
    443: 95.0,    # HTTPS
    22: 70.0,     # SSH
    21: 35.0,     # FTP
    25: 30.0,     # SMTP
    53: 28.0,     # DNS
    110: 22.0,    # POP3
    143: 20.0,    # IMAP
    993: 19.0,    # IMAPS
    995: 18.0,    # POP3S
    587: 17.0,    # SMTP submission
    465: 16.0,    # SMTPS
    8080: 45.0,   # HTTP alt — very common in dev/proxy
    8443: 30.0,   # HTTPS alt
    3306: 25.0,   # MySQL
    5432: 18.0,   # PostgreSQL
    3389: 22.0,   # RDP
    445: 20.0,    # SMB
    139: 15.0,    # NetBIOS
    135: 14.0,    # MS-RPC
    23: 12.0,     # Telnet
    111: 10.0,    # RPCBind
    1433: 12.0,   # MSSQL
    1521: 8.0,    # Oracle
    27017: 10.0,  # MongoDB
    6379: 12.0,   # Redis
    5900: 8.0,    # VNC
    9090: 7.0,    # Management consoles
    8888: 6.0,    # Various web apps
    2222: 5.0,    # Alt SSH
    4443: 4.0,    # Alt HTTPS
    8000: 15.0,   # Dev servers
    8081: 10.0,   # HTTP alt
    9200: 8.0,    # Elasticsearch
    5601: 6.0,    # Kibana
    11211: 5.0,   # Memcached
    6443: 7.0,    # Kubernetes API
    2375: 4.0,    # Docker
    2376: 4.0,    # Docker TLS
}

# Baseline weight for ports not in the frequency table
_BASELINE_WEIGHT = 1.0


def order_sequential(ports: List[int]) -> List[int]:
    """Return ports in ascending numerical order."""
    return sorted(ports)


def order_random(ports: List[int], seed: int = None) -> List[int]:
    """Shuffle ports into a pseudorandom order.

    Uses Fisher-Yates shuffle. Optionally accepts a seed
    for reproducible scan ordering.
    """
    shuffled = list(ports)
    if seed is not None:
        rng = random.Random(seed)
        rng.shuffle(shuffled)
    else:
        random.shuffle(shuffled)
    return shuffled


def order_frequency_weighted(ports: List[int]) -> List[int]:
    """Order ports by empirical probability of being open (highest first).

    Ports with known high frequency in internet-wide surveys are
    scanned first. This maximizes early discovery of open services,
    which is useful for:
    - Faster initial results
    - Early feeding of RTT data into the adaptive timeout model
    - Prioritizing high-value targets when scan time is limited

    Ports not in the frequency table get the baseline weight and
    are ordered by port number as a tiebreaker.
    """
    def sort_key(port):
        weight = PORT_FREQUENCY.get(port, _BASELINE_WEIGHT)
        # Negate weight for descending order, use port as tiebreaker
        return (-weight, port)

    return sorted(ports, key=sort_key)


def order_entropy_distributed(ports: List[int]) -> List[int]:
    """Distribute ports to maximize distance between consecutive probes.

    Uses a stride-based approach inspired by the bit-reversal permutation.
    This spreads probes across the port range so that consecutive probes
    hit distant parts of the range — useful for evading sequential-scan
    detection and for getting a representative sample early.

    The stride is chosen as the largest power of 2 that fits the range,
    producing a permutation where each probe is maximally distant from
    recent probes in port-number space.
    """
    if len(ports) <= 1:
        return list(ports)

    sorted_ports = sorted(ports)
    n = len(sorted_ports)

    # Find stride: largest power of 2 less than n, coprime to n
    stride = 1
    while stride * 2 < n:
        stride *= 2
    # Ensure stride is coprime to n (if n is even, add 1)
    if n % stride == 0:
        stride += 1
    # Fallback: use a prime-like stride
    if math.gcd(stride, n) != 1:
        stride = _find_coprime_stride(n)

    result = []
    idx = 0
    for _ in range(n):
        result.append(sorted_ports[idx])
        idx = (idx + stride) % n

    return result


def _find_coprime_stride(n: int) -> int:
    """Find a stride coprime to n that is roughly n/2 for good distribution."""
    # Start near n/2 and search upward for a coprime
    candidate = max(1, n // 2)
    while candidate < n:
        if math.gcd(candidate, n) == 1:
            return candidate
        candidate += 1
    return 1


STRATEGIES = {
    "sequential": order_sequential,
    "random": order_random,
    "frequency": order_frequency_weighted,
    "entropy": order_entropy_distributed,
}


def apply_strategy(ports: List[int], strategy: str = "sequential") -> List[int]:
    """Apply the named ordering strategy to a list of ports.

    Args:
        ports: List of port numbers to reorder.
        strategy: One of "sequential", "random", "frequency", "entropy".

    Returns:
        Reordered list of ports.
    """
    fn = STRATEGIES.get(strategy)
    if fn is None:
        raise ValueError(
            f"Unknown scan strategy: {strategy!r}. "
            f"Choose from: {', '.join(STRATEGIES.keys())}"
        )
    return fn(ports)
