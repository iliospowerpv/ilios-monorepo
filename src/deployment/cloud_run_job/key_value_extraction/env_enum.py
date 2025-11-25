import enum


class Env(str, enum.Enum):
    """DOCAI environment types."""

    TEST = "TEST"
    DEV = "DEV"
    QA = "QA"
    UAT = "UAT"
    PROD = "PROD"
    LOCAL = "LOCAL"
