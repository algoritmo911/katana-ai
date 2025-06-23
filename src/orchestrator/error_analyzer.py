from enum import Enum
from typing import Dict, Any

class ErrorCriticality(Enum):
    LOW = "low"      # Non-critical, may not require immediate action
    MEDIUM = "medium"  # Requires attention, may impact functionality or performance
    HIGH = "high"    # Critical, requires immediate attention, major impact

ERROR_CLASSIFICATIONS = { # Corrected variable name back
    "TimeoutError": {
        "keywords": ["timeout", "timed out", "deadline exceeded"],
        "description": "The operation exceeded the allocated time.",
        "criticality": ErrorCriticality.MEDIUM,
    },
    "APIError": {
        "keywords": ["api error", "api limit", "service unavailable", "internal server error", "bad gateway"],
        "description": "An error occurred while communicating with an external API or service.",
        "criticality": ErrorCriticality.HIGH,
    },
    "ConnectionError": {
        "keywords": ["connection error", "cannot connect", "host not found", "network is unreachable", "connection refused", "failed to establish"],
        "description": "A network connection problem occurred.",
        "criticality": ErrorCriticality.HIGH,
    },
    "TypeError": {
        "keywords": ["typeerror", "incorrect type", "argument type"],
        "description": "An operation was performed on an object of an inappropriate type.",
        "criticality": ErrorCriticality.MEDIUM,
    },
    "ValueError": {
        "keywords": ["valueerror", "invalid value", "out of range"],
        "description": "An operation received an argument that has the right type but an inappropriate value.",
        "criticality": ErrorCriticality.MEDIUM,
    },
    "FileNotFoundError": {
        "keywords": ["file not found", "no such file"],
        "description": "A required file or directory was not found.",
        "criticality": ErrorCriticality.LOW,
    },
    "PermissionError": {
        "keywords": ["permission denied", "not permitted"],
        "description": "An attempt was made to operate on a file without the requisite permissions.",
        "criticality": ErrorCriticality.MEDIUM,
    },
    "AuthenticationError": {
        "keywords": ["authentication failed", "unauthorized", "401", "invalid credentials"],
        "description": "Failed to authenticate with a service or API.",
        "criticality": ErrorCriticality.HIGH,
    },
    "ConfigurationError": {
        "keywords": ["configuration error", "invalid config", "missing setting"],
        "description": "There is an issue with the application's configuration.",
        "criticality": ErrorCriticality.HIGH,
    },
    # Add more specific error types as needed
}

DEFAULT_ERROR_CLASSIFICATION = {
    "type": "UnknownError",
    "description": "An unrecognized or uncategorized error occurred.",
    "criticality": ErrorCriticality.LOW,
}

def classify_error(error_details: str) -> Dict[str, Any]:
    """
    Classifies an error based on its details string.

    Args:
        error_details: A string containing information about the error.
                       This is typically the exception message.

    Returns:
        A dictionary containing:
            - 'type' (str): The classified error type (e.g., "TimeoutError").
            - 'description' (str): A human-readable explanation of the error.
            - 'criticality' (ErrorCriticality): The severity of the error.
            - 'original_details' (str): The original error_details string.
    """
    if not isinstance(error_details, str):
        error_details = str(error_details) # Ensure it's a string

    lower_error_details = error_details.lower()

    for error_type, config in ERROR_CLASSIFICATIONS.items():
        for keyword in config["keywords"]:
            if keyword in lower_error_details:
                return {
                    "type": error_type,
                    "description": config["description"],
                    "criticality": config["criticality"].value, # Store the string value
                    "original_details": error_details,
                }

    # If no specific classification is found, return a default one
    return {
        "type": DEFAULT_ERROR_CLASSIFICATION["type"],
        "description": DEFAULT_ERROR_CLASSIFICATION["description"],
        "criticality": DEFAULT_ERROR_CLASSIFICATION["criticality"].value, # Store the string value
        "original_details": error_details,
    }

if __name__ == '__main__':
    # Example Usage
    errors_to_test = [
        "Operation timed out after 30s",
        "APIError: Request limit reached for /v1/complete",
        "ConnectionError: Could not connect to host database.internal:5432",
        "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
        "ValueError: math domain error",
        "FileNotFoundError: [Errno 2] No such file or directory: 'input.txt'",
        "PermissionError: [Errno 13] Permission denied: '/root/secret.key'",
        "Authentication failed: Invalid API key.",
        "Invalid configuration: Missing 'DATABASE_URL' setting.",
        "Some other weird problem that we have not seen before."
    ]

    for err_detail in errors_to_test:
        classification = classify_error(err_detail)
        print(f"Error: \"{err_detail}\"")
        print(f"  Type: {classification['type']}")
        print(f"  Description: {classification['description']}")
        print(f"  Criticality: {classification['criticality']}")
        print("-" * 30)

    # Test with a non-string input
    class CustomException(Exception):
        pass

    custom_err = CustomException("This is a custom exception object.")
    classification = classify_error(custom_err)
    print(f"Error: \"{str(custom_err)}\"")
    print(f"  Type: {classification['type']}")
    print(f"  Description: {classification['description']}")
    print(f"  Criticality: {classification['criticality']}")
    print("-" * 30)
