def pagination_details(skip: int, limit: int, total: int) -> dict:
    """Basic pagination response"""
    return {
        "skip": skip,
        "limit": limit,
        "total": total,
    }
