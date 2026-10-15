from rest_framework.permissions import BasePermission


class IsAdministrator(BasePermission):
    message = "Apenas administradores podem realizar esta ação."

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_admin)


class IsTechnicianOrAdministrator(BasePermission):
    message = "Apenas técnicos ou administradores podem realizar esta ação."

    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated and (request.user.is_technician or request.user.is_admin)
        )
