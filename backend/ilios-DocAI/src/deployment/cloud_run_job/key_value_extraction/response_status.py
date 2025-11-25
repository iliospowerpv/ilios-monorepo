import enum


class Status(str, enum.Enum):
    """Kye-value extraction job statuses, that are passed to iliOS backend."""

    COMPLETED = "Completed"
    PROCESSING_FAILED = "Processing Failed"
    PROCESSING_TIMEOUT = "Processing Timeout"
    UNPROCESSABLE_FILE = "Unprocessable File"
