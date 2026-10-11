import enum

from sqlalchemy import Enum as SQLAlchemyEnum


class UserRole(enum.Enum):
    admin = 1
    tourist = 2


USER_ROLE_ENUM = SQLAlchemyEnum(
    UserRole,
    name="userrole",
    values_callable=lambda roles: [str(role.value) for role in roles],
)
