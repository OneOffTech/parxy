class ParsingException(Exception):
    """Exception raised for parsing errors.

    This exception is raised when parsing document fails.

    Attributes
    ----------
    message : str
        Explanation of the parsing error
    service : str
        Name of the service that failed (e.g., 'LlamaParse', 'PDFAct')
    details : dict, optional
        Additional details about the error, such as response data or error codes

    Example
    ---------
    try:
        # API call fails
        raise ParsingException(
            message="Error while parsing",
            service="LlamaParse",
            details={"error_code": "ERR001", "response": {"detail": "File not accessible"}}
        )
    except ParsingException as e:
        print(e)  # Will print: "Parsing failed for LlamaParse: Error while parsing\nDetails: {...}"
    """

    def __init__(self, message: str, service: str, details: dict = None):
        """Initialize the authentication error.

        Parameters
        ----------
        message : str
            Human-readable error message
        service : str
            Name of the service that failed
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
        base_message = f'Parsing failed for {self.service}: {self.message}'
        if self.details:
            return f'{base_message}\nDetails: {self.details}'
        return base_message
