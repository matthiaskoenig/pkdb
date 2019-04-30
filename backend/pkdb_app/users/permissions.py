from rest_framework import permissions

def is_allowed_method(request):
    allowed_methods = ["PUT",*permissions.SAFE_METHODS]
    if request.method in allowed_methods :
        return True
    return False

class IsUserOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            return True

        return obj == request.user

class IsAdminOrCreator(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):

        if is_allowed_method(request):
            return True

        user = request.user
        return user.is_staff or (user == obj.creator)


class IsAdminOrCreatorOrCurator(permissions.BasePermission):
    """
    for study and reference
    """

    def has_object_permission(self, request, view, obj):

        if is_allowed_method(request):
            return True

        user = request.user
        try:
            # for study model
            allowed_user = (user == obj.creator) or (user in obj.curators.all())
        except AttributeError:
            # for reference model
            allowed_user = (user == obj.study.first().creator) or (user in obj.study.first().curators.all())

        return user.is_staff or allowed_user
