from rest_framework import permissions


class FilePermissions(permissions.BasePermission):
    """
    files and pdfs related to the publication can be get if you are the creator, admin or the licences of
    the publication is open
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS: # "GET, HEAD, OPTIONS are safe methods
            return obj.creator == request.user or request.user.is_staff or self.licence == "open"

        #else:
        #    return obj.archive.user == request.user or request.user.is_staff












