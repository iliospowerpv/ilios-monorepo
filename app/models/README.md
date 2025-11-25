# Database Models

This package contains database entity definitions described with
[SQLAlchemy declarative base](https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/basic_use.html).

**NOTE:** Each logical domain/entity group must be defined in a separate file.

### Here are few tips to use for the DB structure description:

#### 1. Use native DB types where it's applicable
For examples, you need to add field `rating` which is decimal value (e.g. 4.25). As a Python-minded developer,
you might have a temptation to use `sqlalchemy.Float` class. And that might work, but with some tricky side effects:
Float is not precise in PostgreSQL, leading to rounding issues, meaning you pass 4.25 but it stores 4. In this case,
to prevent unexpected behaviour solution is to use SQL-native types, such as `DECIMAL` or `NUMERIC`:
they store numbers exactly as written, preventing rounding errors.

More details about Float and precision can be found in the [docs](https://www.postgresql.org/docs/12/datatype-numeric.html#DATATYPE-FLOAT).
