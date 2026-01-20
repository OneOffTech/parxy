from typing import Optional


class QuotaExceededException(Exception):
    """Exception raised when account quota or balance is insufficient.

    This exception should be raised when a service returns a 402 status code
    or indicates that the account balance, credits, or quota has been exhausted.

    Attributes
    ----------
    message : str
        Explanation of the quota error
    service : str
        Name of the service where quota was exceeded (e.g., 'LlamaParse', 'LandingAI')
    details : dict, optional
        Additional details about the error, such as response data or remaining quota

    Example
    ---------
    try:
        # API call fails with 402
        raise QuotaExceededException(
            message="User balance is insufficient",
            service="LandingAI",
            details={"error_code": 402, "response": {"error": "Payment Required"}}
        )
    except QuotaExceededException as e:
        print(e)  # Will print: "Quota exceeded for LandingAI: User balance is insufficient"
    """

    def __init__(
        self,
        message: str,
        service: str,
        details: Optional[dict] = None,
    ):
        """Initialize the quota exceeded error.

        Parameters
        ----------
        message : str
            Human-readable error message
        service : str
            Name of the service where quota was exceeded
        details : dict, optional
            Additional error details, by default None
        """
        self.message = message
        self.service = service
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return a string representation of the error.

        Returns
        -------
        str
            Formatted error message including service name
        """
        base_message = f'Quota exceeded for {self.service}: {self.message}'
        if self.details:
            return f'{base_message}\nDetails: {self.details}'
        return base_message
