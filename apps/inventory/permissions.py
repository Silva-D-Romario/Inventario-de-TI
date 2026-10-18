from rest_framework.permissions import SAFE_METHODS, BasePermission


class MasterDataPermission(BasePermission):
    message = "Apenas administradores podem alterar categorias, setores e status."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_admin


class AssetPermission(BasePermission):
    message = "Você não possui permissão para alterar ativos."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return request.user.is_admin
        return request.user.is_admin or request.user.is_technician
