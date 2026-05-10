REPORTER = "reporter"
DEVELOPER = "developer"
PRODUCT_OWNER = "po"
LEGACY_BA = "ba"
ADMIN = "admin"

STAFF_ROLES = {DEVELOPER, PRODUCT_OWNER, LEGACY_BA, ADMIN}
MANAGER_ROLES = {PRODUCT_OWNER, LEGACY_BA, ADMIN}


def is_ba_or_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.role in MANAGER_ROLES)


def is_product_owner_or_admin(user) -> bool:
    return is_ba_or_admin(user)


def is_staff_role(user) -> bool:
    return bool(user and user.is_authenticated and user.role in STAFF_ROLES)
