from typing import Optional


class RateLimitException(Exception):
    """Exception raised when API rate limits are exceeded.

    This exception should be raised when a service returns a 429 status code
    or indicates that the request rate or quota has been exceeded.

    Attributes
    ----------
    message : str
        Explanation of the rate limit error
    service : str
        Name of the service where rate limit was hit (e.g., 'LlamaParse', 'LandingAI')
    retry_after : int, optional
        Number of seconds to wait before retrying, if provided by the service
    details : dict, optional
        Additional details about the error, such as response data or error codes

    Example
    ---------
    try:
        # API call fails with 429
        raise RateLimitException(
            message="Rate limit exceeded",
            service="LandingAI",
            retry_after=60,
            details={"error_code": 429, "response": {"error": "Rate limit exceeded"}}
        )
    except RateLimitException as e:
        print(e)  # Will print: "Rate limit exceeded for LandingAI: Rate limit exceeded"
        if e.retry_after:
            print(f"Retry after {e.retry_after} seconds")
    """

    def __init__(
        self,
        message: str,
        service: str,
        retry_after: Optional[int] = None,
        details: dict = None,
    ):
        """Initialize the rate limit error.

        Parameters
        ----------
        message : str
            Human-readable error message
        service : str
            Name of the service where rate limit was hit
        retry_after : int, optional
            Seconds to wait before retrying, by default None
        details : dict, optional
            Additional error details, by default None
        """
        self.message = message
        self.service = service
        self.retry_after = retry_after
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return a string representation of the error.

        Returns
        -------
        str
            Formatted error message including service name and retry info
        """
        base_message = f'Rate limit exceeded for {self.service}: {self.message}'
        if self.retry_after:
            base_message = f'{base_message} (retry after {self.retry_after}s)'
        if self.details:
            return f'{base_message}\nDetails: {self.details}'
        return base_message
