from datetime import datetime


class DateValidationError(Exception):
    pass


def validate_yyyy_mm_dd(date_str: str) -> str:
    """
    Validates a date string in YYYY-MM-DD format.
    Returns the original string if valid, raises DateValidationError if invalid.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError as err:
        raise DateValidationError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD.") from err
