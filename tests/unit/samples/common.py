BODY_EMAIL_PATTERN_MISMATCH_ERR = (
    "Validation error: body.email - value is not a valid email address: The email address is not valid. It must "
    "have exactly one @-sign."
)
QUERY_EMAIL_PATTERN_MISMATCH_ERR = (
    "Validation error: query.email - value is not a valid email address: The email address is not valid. It must "
    "have exactly one @-sign."
)

EMAIL_LENGTH_ERROR = "Validation error: body.email - Value should have at most 100 items after validation, not 101"
LONGER_THAN_100_CHARS_EMAIL = (
    "email@longermaillongermaillo.ngermaillongermailong.maillongermaillongermailil.maillongermaillonge.ccc"
)

# TODO integrate in every mocked gcp link
TEST_GCP_LINK = "https://storage.googleapis.com/upload"


class UserFakeModel:
    """Fake user model with read and write attrs capabilities."""

    email = None
    is_registered = False
    hashed_password = None

    def __init__(self, **kwargs):
        for kw, arg in kwargs.items():
            setattr(self, kw, arg)


def enum_to_str(enum_):
    """Wrap enum values into string literals wrapper into single quotes"""
    return ", ".join([f"'{type_.value}'" for type_ in enum_])


def enum_to_message(enum_):
    """Extends `enum_to_str` method, and replaced last comma with `or`"""
    available_options = enum_to_str(enum_)
    li = available_options.rsplit(",", 1)
    return " or".join(li)
