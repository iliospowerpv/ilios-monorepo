from enum import Enum


class CoTerminusComparisonStatuses(Enum):
    """Statuses of the text comparison for the co-terminus"""

    equal = "Equal"
    not_equal = "Not Equal"
    ambiguous = "Ambiguous"
    na = "N/A"
    pending = "Pending"
    error = "Error"
