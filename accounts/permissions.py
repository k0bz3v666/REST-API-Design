from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Читати можуть усі, змінювати дані — лише адміністратори (is_staff)."""

    message = "Змінювати каталог можуть лише адміністратори."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)
