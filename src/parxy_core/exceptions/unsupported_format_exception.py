class UnsupportedFormatException(Exception):
    """Exception raised for file format not supported.

    This exception is raised when a file is of a format not supported by the parsing service.

    Attributes
    ----------
    message : str
        Explanation error
    service : str
        Name of the service that failed (e.g., 'LlamaParse', 'PDFAct')
    details : dict, optional
        Additional details about the error, such as response data or error codes

    Example
    ---------
    try:
        # API call fails
        raise UnsupportedFormatException(
            message="Format [text/markdown] not supported.",
            service="LlamaParse",
            details={"error_code": "ERR001", "response": {"detail": "Unknown format"}}
        )
    except UnsupportedFormatException as e:
        print(e)  # Will print: "Unsupported format for LlamaParse: Format [text/markdown] not supported.\nDetails: {...}"
    """

    def __init__(self, message: str, service: str, details: dict = None):
        """Initialize the exception.

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
        base_message = f'Unsupported format for {self.service}: {self.message}'
        if self.details:
            return f'{base_message}\nDetails: {self.details}'
        return base_message
