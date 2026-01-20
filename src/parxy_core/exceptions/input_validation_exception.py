from typing import Optional


class InputValidationException(Exception):
    """Exception raised when input fails service validation constraints.

    This exception should be raised when a service returns a 422 status code
    or indicates that the input doesn't meet requirements such as page limits,
    file size limits, or other validation constraints.

    Attributes
    ----------
    message : str
        Explanation of the validation error
    service : str
        Name of the service where validation failed (e.g., 'LlamaParse', 'LandingAI')
    details : dict, optional
        Additional details about the error, such as constraints or limits

    Example
    ---------
    try:
        # API call fails with 422
        raise InputValidationException(
            message="PDF must not exceed 100 pages",
            service="LandingAI",
            details={"max_pages": 100, "actual_pages": 150}
        )
    except InputValidationException as e:
        print(e)  # Will print: "Input validation failed for LandingAI: PDF must not exceed 100 pages"
    """

    def __init__(
        self,
        message: str,
        service: str,
        details: Optional[dict] = None,
    ):
        """Initialize the input validation error.

        Parameters
        ----------
        message : str
            Human-readable error message
        service : str
            Name of the service where validation failed
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
        base_message = f'Input validation failed for {self.service}: {self.message}'
        if self.details:
            return f'{base_message}\nDetails: {self.details}'
        return base_message
