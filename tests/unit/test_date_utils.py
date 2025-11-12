import pytest

from nightscout_backup_bot.utils.date_utils import DateValidationError, validate_yyyy_mm_dd


def test_valid_date() -> None:
    assert validate_yyyy_mm_dd("2025-11-11") == "2025-11-11"
    assert validate_yyyy_mm_dd("2025-01-01") == "2025-01-01"


def test_invalid_date_format() -> None:
    with pytest.raises(DateValidationError):
        validate_yyyy_mm_dd("11-11-2025")
    with pytest.raises(DateValidationError):
        validate_yyyy_mm_dd("2025/11/11")
    with pytest.raises(DateValidationError):
        validate_yyyy_mm_dd("2025-13-01")
    with pytest.raises(DateValidationError):
        validate_yyyy_mm_dd("")
