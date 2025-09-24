class FileNotFoundException(FileNotFoundError):
    """Exception raised for file not found errors.

    This exception is raised when a file cannot be accessed for parsing.

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
        raise FileNotFoundException(
            message="File [path] not found or accessible.",
            service="LlamaParse",
            details={"error_code": "ERR001", "response": {"detail": "File not accessible"}}
        )
    except FileNotFoundException as e:
        print(e)  # Will print: "File not found failed for LlamaParse: File [path] not found or accessible.\nDetails: {...}"
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
