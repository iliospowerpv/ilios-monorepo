from enum import Enum
from typing import Annotated, Type

from fastapi import HTTPException, Query, status

from app.schema.common import OrderDirectionEnum
from app.static import DEFAULT_PAGINATION_LIMIT, DEFAULT_PAGINATION_SKIP

BIGINT_UPPER_RANGE = 9223372036854775807


def validate_query_params(order_by: Type[Enum]):
    def wrapper(
        skip: int = DEFAULT_PAGINATION_SKIP,
        limit: int = DEFAULT_PAGINATION_LIMIT,
        order_by: Annotated[order_by | None, Query(enum=list(order_by))] = None,
        order_direction: Annotated[OrderDirectionEnum | None, Query(enum=list(OrderDirectionEnum))] = None,
    ):
        """Custom validator function to check the query parameters and their combinations."""
        if not order_by and order_direction:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "It is required to have order_by column specified first before applying ordering direction",
            )
        validate_skip_and_limit(skip, limit)
        return skip, limit, order_by, order_direction

    return wrapper


def validate_skip_and_limit(skip: int = DEFAULT_PAGINATION_SKIP, limit: int = DEFAULT_PAGINATION_LIMIT):  # noqa: FNE007
    """Check skip and limit are values allowed by the sqlalchemy to used as pagination params:
    positive and less than max integer value"""
    if any((skip < 0, limit < 0, skip > BIGINT_UPPER_RANGE, limit > BIGINT_UPPER_RANGE)):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"It is required skip/limit input be a valid positive number and no longer than {BIGINT_UPPER_RANGE}.",
        )
