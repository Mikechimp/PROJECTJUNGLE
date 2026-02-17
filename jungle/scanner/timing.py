"""Timing engine for controlled port scanning.

Provides mathematical models for scan timing control:
- Timing profiles (T0-T5) with tunable parameters
- Adaptive timeout using EWMA of RTT (RFC 6298 inspired)
- Token bucket rate limiter
- Inter-probe delay with configurable jitter distribution
"""

import math
import time
import random
import threading
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class TimingProfile(IntEnum):
    """Predefined timing profiles (T0-T5), modeled after nmap's approach
    but with full mathematical control over every parameter."""
    PARANOID = 0   # Serial, 5-minute inter-probe delay
    SNEAKY = 1     # Serial, 15s inter-probe delay
    POLITE = 2     # Serial, 400ms inter-probe delay
    NORMAL = 3     # Parallelized, no artificial delay
    AGGRESSIVE = 4 # Parallelized, tight timeouts, high rate
    INSANE = 5     # Parallelized, minimal timeouts, max rate


@dataclass
class TimingParams:
    """Full set of tunable timing parameters.

    All delays are in seconds. Users can override any individual
    parameter while inheriting defaults from a timing profile.
    """
    # Rate control
    max_rate: float = 0.0          # Max probes/sec (0 = unlimited)
    min_rate: float = 0.0          # Min probes/sec (0 = no floor)
    max_parallelism: int = 50      # Max concurrent probes
    min_parallelism: int = 1       # Min concurrent probes

    # Inter-probe delay
    probe_delay: float = 0.0      # Base delay between probes (seconds)
    jitter_type: str = "none"     # "none", "uniform", "gaussian"
    jitter_factor: float = 0.0    # Jitter magnitude (fraction of probe_delay)

    # Timeout control
    initial_timeout: float = 2.0  # Starting timeout before any RTT data
    min_timeout: float = 0.1      # Floor for adaptive timeout
    max_timeout: float = 10.0     # Ceiling for adaptive timeout

    # EWMA parameters (RFC 6298 inspired)
    rtt_alpha: float = 0.125      # Smoothing factor for SRTT (1/8)
    rtt_beta: float = 0.25        # Smoothing factor for RTTVAR (1/4)
    rtt_k: float = 4.0            # Variance multiplier for RTO calc

    # Adaptive parallelism
    congestion_threshold: float = 0.30  # Drop rate triggering backoff
    backoff_factor: float = 0.5         # Multiply parallelism by this on congestion
    recovery_factor: float = 1.1        # Multiply parallelism by this on success


# Preset configurations for each timing profile
TIMING_PRESETS = {
    TimingProfile.PARANOID: TimingParams(
        max_parallelism=1,
        min_parallelism=1,
        probe_delay=300.0,
        jitter_type="uniform",
        jitter_factor=0.1,
        initial_timeout=10.0,
        max_timeout=30.0,
    ),
    TimingProfile.SNEAKY: TimingParams(
        max_parallelism=1,
        min_parallelism=1,
        probe_delay=15.0,
        jitter_type="uniform",
        jitter_factor=0.2,
        initial_timeout=5.0,
        max_timeout=15.0,
    ),
    TimingProfile.POLITE: TimingParams(
        max_parallelism=1,
        min_parallelism=1,
        probe_delay=0.4,
        jitter_type="uniform",
        jitter_factor=0.15,
        initial_timeout=3.0,
        max_timeout=10.0,
    ),
    TimingProfile.NORMAL: TimingParams(
        max_parallelism=50,
        probe_delay=0.0,
        initial_timeout=2.0,
    ),
    TimingProfile.AGGRESSIVE: TimingParams(
        max_parallelism=200,
        probe_delay=0.0,
        initial_timeout=1.0,
        min_timeout=0.05,
        max_timeout=3.0,
        congestion_threshold=0.5,
    ),
    TimingProfile.INSANE: TimingParams(
        max_parallelism=500,
        probe_delay=0.0,
        initial_timeout=0.3,
        min_timeout=0.02,
        max_timeout=1.5,
        congestion_threshold=0.7,
    ),
}


class AdaptiveTimeout:
    """Computes adaptive timeout using Jacobson/Karels algorithm (RFC 6298).

    Models the round-trip time as a smoothed estimate with variance tracking:
        SRTT     = (1 - alpha) * SRTT + alpha * sample_rtt
        RTTVAR   = (1 - beta) * RTTVAR + beta * |sample_rtt - SRTT|
        RTO      = SRTT + K * RTTVAR

    This gives a timeout that tracks the observed network conditions and
    automatically widens when RTT becomes variable (congestion, filtering).
    """

    def __init__(self, params: TimingParams):
        self.params = params
        self._srtt: Optional[float] = None    # Smoothed RTT
        self._rttvar: Optional[float] = None  # RTT variance
        self._samples = 0
        self._lock = threading.Lock()

    def record_rtt(self, rtt: float) -> None:
        """Feed an RTT sample into the EWMA estimator."""
        with self._lock:
            if self._srtt is None:
                # First sample: initialize per RFC 6298 section 2.2
                self._srtt = rtt
                self._rttvar = rtt / 2.0
            else:
                alpha = self.params.rtt_alpha
                beta = self.params.rtt_beta
                self._rttvar = (1 - beta) * self._rttvar + beta * abs(rtt - self._srtt)
                self._srtt = (1 - alpha) * self._srtt + alpha * rtt
            self._samples += 1

    def get_timeout(self) -> float:
        """Compute the current adaptive timeout (RTO)."""
        with self._lock:
            if self._srtt is None:
                return self.params.initial_timeout

            rto = self._srtt + self.params.rtt_k * self._rttvar
            return max(self.params.min_timeout, min(rto, self.params.max_timeout))

    @property
    def srtt(self) -> Optional[float]:
        """Current smoothed RTT estimate, or None if no samples yet."""
        with self._lock:
            return self._srtt

    @property
    def rttvar(self) -> Optional[float]:
        """Current RTT variance estimate, or None if no samples yet."""
        with self._lock:
            return self._rttvar

    @property
    def samples(self) -> int:
        with self._lock:
            return self._samples


class TokenBucketRateLimiter:
    """Token bucket algorithm for probe rate control.

    Tokens are generated at a fixed rate (max_rate per second).
    Each probe consumes one token. If the bucket is empty, the
    caller blocks until a token is available.

    The bucket has a max capacity (burst) to allow short bursts
    above the sustained rate.
    """

    def __init__(self, rate: float, burst: int = 10):
        """
        Args:
            rate: Maximum sustained probes per second.
            burst: Maximum tokens that can accumulate (burst capacity).
        """
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a token is available, then consume it."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                # Calculate wait time for next token
                wait = (1.0 - self._tokens) / self.rate
            time.sleep(wait)

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now


class AdaptiveParallelism:
    """Dynamically adjusts concurrency based on observed drop rates.

    Uses a congestion-avoidance model:
    - When drop rate exceeds threshold → multiply parallelism by backoff_factor
    - When drop rate is below threshold → multiply by recovery_factor
    - Bounded by [min_parallelism, max_parallelism]

    Drop rate is computed over a sliding window of recent probes.
    """

    def __init__(self, params: TimingParams, window_size: int = 100):
        self.params = params
        self._window_size = window_size
        self._results: list = []  # True = success, False = drop/timeout
        self._current = float(params.max_parallelism)
        self._lock = threading.Lock()

    def record(self, success: bool) -> None:
        """Record whether a probe succeeded or timed out."""
        with self._lock:
            self._results.append(success)
            if len(self._results) > self._window_size:
                self._results.pop(0)
            self._adjust()

    def _adjust(self) -> None:
        """Recalculate parallelism from the current window."""
        if len(self._results) < 10:
            return
        drops = sum(1 for r in self._results if not r)
        drop_rate = drops / len(self._results)

        if drop_rate > self.params.congestion_threshold:
            self._current *= self.params.backoff_factor
        else:
            self._current *= self.params.recovery_factor

        self._current = max(
            self.params.min_parallelism,
            min(self.params.max_parallelism, self._current),
        )

    @property
    def current(self) -> int:
        """Current recommended parallelism level."""
        with self._lock:
            return max(1, int(self._current))


class ProbeDelayEngine:
    """Computes inter-probe delays with configurable jitter.

    Supports three jitter distributions:
    - none:     delay = base_delay (deterministic)
    - uniform:  delay = base_delay * (1 + U(-jitter, +jitter))
    - gaussian: delay = base_delay * (1 + N(0, jitter))
                clipped to [0, 2 * base_delay] to avoid negatives
    """

    def __init__(self, params: TimingParams):
        self.params = params

    def wait(self) -> None:
        """Sleep for the computed inter-probe delay."""
        delay = self.compute_delay()
        if delay > 0:
            time.sleep(delay)

    def compute_delay(self) -> float:
        """Calculate the next inter-probe delay in seconds."""
        base = self.params.probe_delay
        if base <= 0:
            return 0.0

        jf = self.params.jitter_factor
        if jf <= 0 or self.params.jitter_type == "none":
            return base

        if self.params.jitter_type == "uniform":
            # Uniform distribution: base * (1 + U(-jf, jf))
            multiplier = 1.0 + random.uniform(-jf, jf)
        elif self.params.jitter_type == "gaussian":
            # Gaussian distribution: base * (1 + N(0, jf)), clipped
            multiplier = 1.0 + random.gauss(0, jf)
        else:
            multiplier = 1.0

        return max(0.0, base * multiplier)


class TimingEngine:
    """Unified timing controller that combines all timing subsystems.

    Provides a single interface for the port scanner to:
    - Get the current adaptive timeout
    - Wait for rate limiting
    - Apply inter-probe delay with jitter
    - Query recommended parallelism
    - Record probe results for adaptation
    """

    def __init__(self, params: Optional[TimingParams] = None,
                 profile: TimingProfile = TimingProfile.NORMAL):
        if params is None:
            params = TimingParams(**TIMING_PRESETS[profile].__dict__)
        self.params = params
        self.adaptive_timeout = AdaptiveTimeout(params)
        self.rate_limiter = (
            TokenBucketRateLimiter(params.max_rate)
            if params.max_rate > 0 else None
        )
        self.parallelism = AdaptiveParallelism(params)
        self.probe_delay = ProbeDelayEngine(params)

    def before_probe(self) -> None:
        """Call before sending a probe. Handles rate limiting and delay."""
        if self.rate_limiter:
            self.rate_limiter.acquire()
        self.probe_delay.wait()

    def after_probe(self, rtt: Optional[float], success: bool) -> None:
        """Call after a probe completes. Feeds data into adaptive models.

        Args:
            rtt: Round-trip time in seconds, or None if timed out.
            success: True if the port responded (open or closed), False if timeout.
        """
        if rtt is not None:
            self.adaptive_timeout.record_rtt(rtt)
        self.parallelism.record(success)

    def get_timeout(self) -> float:
        """Get the current adaptive timeout value."""
        return self.adaptive_timeout.get_timeout()

    def get_parallelism(self) -> int:
        """Get the current recommended thread count."""
        return self.parallelism.current
