from datetime import datetime, timezone


# TODO IOSP1-4149
def get_utc_now():
    """Utility to return current datetime in UTC"""
    return datetime.now(timezone.utc)
