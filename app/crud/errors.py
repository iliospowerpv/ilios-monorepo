"""Location of all common exceptions and errors classes."""


class BaseCRUDError(Exception):
    """BaseCRUD exception super-class."""

    def __init__(self, message: str) -> None:
        self.message = message


class UniqueConstraintViolationError(BaseCRUDError):
    """Error for the Unique constraint violation."""
