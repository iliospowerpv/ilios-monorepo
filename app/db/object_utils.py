def as_dict(sqlalchemy_object):
    """Serialize SQLAlchemy object to the dict, excluding protected fields"""
    return {
        key: value
        for key, value in sqlalchemy_object.__dict__.items()
        if not (key.startswith("_") or key.startswith("__"))
    }
