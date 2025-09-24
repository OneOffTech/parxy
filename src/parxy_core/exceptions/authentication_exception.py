class AuthenticationException(Exception):
    """Exception raised for authentication errors.

    This exception should be raised when authentication fails with external services
    or APIs, such as invalid API keys, expired tokens, or insufficient permissions.

    Attributes
    ----------
    message : str
        Explanation of the authentication error
    service : str
        Name of the service where authentication failed (e.g., 'LlamaParse', 'PDFAct')
    details : dict, optional
        Additional details about the error, such as response data or error codes

    Example
    ---------
    try:
        # API call fails
        raise AuthenticationException(
            message="Invalid API key provided",
            service="LlamaParse",
            details={"error_code": "AUTH001", "response": {"detail": "Invalid authentication token"}}
        )
    except AuthenticationException as e:
        print(e)  # Will print: "Authentication failed for LlamaParse: Invalid API key provided\nDetails: {...}"
    """

    def __init__(self, message: str, service: str, details: dict = None):
        """Initialize the authentication error.

        Parameters
        ----------
        message : str
            Human-readable error message
        service : str
            Name of the service where authentication failed
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
            Formatted error message including service name and details
        """
        base_message = f'Authentication failed for {self.service}: {self.message}'
        if self.details:
            return f'{base_message}\nDetails: {self.details}'
        return base_message
