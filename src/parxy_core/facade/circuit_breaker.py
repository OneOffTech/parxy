"""Circuit breaker for batch processing to short-circuit systemic driver failures."""

import threading

from parxy_core.exceptions import (
    AuthenticationException,
    QuotaExceededException,
    RateLimitException,
)

IMMEDIATE_TRIP_EXCEPTIONS = (
    AuthenticationException,
    QuotaExceededException,
    RateLimitException,
)


class CircuitBreakerState:
    """Per-batch circuit breaker that tracks driver-level failures.

    When a driver raises an exception that indicates a systemic problem
    (bad credentials, exhausted quota, rate limit), the circuit opens for
    that driver and all subsequent tasks targeting it are short-circuited
    with the original tripping exception.

    Thread-safe: guards internal state with a lock so concurrent workers
    in ``ThreadPoolExecutor`` can safely read and write.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._open_drivers: dict[str, Exception] = {}

    def is_open(self, driver_name: str) -> bool:
        """Return True if the circuit is open (tripped) for *driver_name*."""
        with self._lock:
            return driver_name in self._open_drivers

    def get_trip_exception(self, driver_name: str) -> Exception | None:
        """Return the exception that tripped the circuit, or None."""
        with self._lock:
            return self._open_drivers.get(driver_name)

    def record_failure(self, driver_name: str, exception: Exception) -> None:
        """Record a failure and trip the circuit if the exception warrants it.

        Only exceptions listed in ``IMMEDIATE_TRIP_EXCEPTIONS`` cause the
        circuit to open.  Per-file errors (e.g. ``FileNotFoundException``)
        are ignored.
        """
        if isinstance(exception, IMMEDIATE_TRIP_EXCEPTIONS):
            with self._lock:
                if driver_name not in self._open_drivers:
                    self._open_drivers[driver_name] = exception
