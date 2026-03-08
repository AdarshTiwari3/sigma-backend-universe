from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    The Global Registry for all SQLAlchemy models.
    Models in src/app/models/ will inherit from this.
    """

    # No `pass` needed. The docstring above satisfies the Python parser.
