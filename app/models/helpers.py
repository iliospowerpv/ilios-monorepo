"""Common logic for several models"""

from sqlalchemy import DateTime
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import expression


class utcnow(expression.FunctionElement):  # noqa: N801
    """A function to get current timestamp"""

    type = DateTime()
    inherit_cache = True


@compiles(utcnow, "postgresql")
def pg_utcnow(element, compiler, **kw):  # noqa: U100
    """Compiling the function for postgresql"""
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"
