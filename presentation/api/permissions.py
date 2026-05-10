from rest_framework.permissions import SAFE_METHODS, BasePermission

from shared_kernel.roles import is_ba_or_admin, is_staff_role


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class IsBAOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_ba_or_admin(request.user)


class BugObjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == "admin":
            return True
        if request.method in SAFE_METHODS:
            if obj.reporter_id == user.id:
                return True
            if obj.status in {"resolved", "verified", "closed"}:
                return True
            return is_staff_role(user) and user.company_id == obj.company_id
        return is_ba_or_admin(user) or obj.reporter_id == user.id
