"""Permission classes and helpers that grant access to studies and their data by user role."""

from django_elasticsearch_dsl_drf.utils import DictionaryProxy
from elasticsearch_dsl import AttrDict
from rest_framework import permissions

from pkdb_app.studies.models import OPEN, Study
from pkdb_app.users.models import PUBLIC


def is_allowed_method(request):
    """Return True for PUT and the safe HTTP methods (GET, HEAD, OPTIONS)."""
    allowed_methods = ["PUT", *permissions.SAFE_METHODS]
    return request.method in allowed_methods


class IsUserOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """Grant safe methods to everybody, write access only to the user who is the object itself."""

    def has_object_permission(self, request, view, obj):
        """Grant safe methods to everybody and write access to the user who is obj itself."""
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj == request.user


class IsAdminOrCreator(permissions.IsAuthenticatedOrReadOnly):
    """Grant PUT and safe methods generally, other writes to staff and the object's creator."""

    def has_object_permission(self, request, view, obj):
        """Grant PUT and safe methods generally, other writes to staff and the creator."""
        if is_allowed_method(request):
            return True

        user = request.user
        return user.is_staff or (user == obj.creator)


class IsAdminOrCreatorOrCurator(permissions.IsAuthenticatedOrReadOnly):
    """Grant PUT and safe methods generally, other writes to staff, creators and curators.

    Used for the study and reference models.
    """

    def has_object_permission(self, request, view, obj):
        """Grant staff and, for objects with a study, the study's creator and curators write access."""
        if is_allowed_method(request):
            return True

        # for reference model
        if hasattr(obj, "study"):
            allowed_user = (request.user == obj.study.creator) or (
                request.user in obj.study.curators.all()
            )
        else:
            allowed_user = False

        return request.user.is_staff or allowed_user


class StudyPermission(permissions.IsAuthenticatedOrReadOnly):
    """Grant access to an object based on the requesting user's role on its study."""

    def has_object_permission(self, request, view, obj):
        """Delegate to the study of obj, if it has one, and check the user's role there."""
        if hasattr(obj, "study") and obj.study:
            obj = obj.study

        return study_permissions(request, obj)


def study_permissions(request, obj):
    """Look up the permission for the requesting user's role on the given study."""
    study_permissions = {
        "admin": admin_permission(),
        "basic": basic_permission(request, obj),
        "reviewer": reviewer_permission(request, obj),
        "anonymous": anonymous_permissions(request, obj),
    }

    return study_permissions[user_group(request.user)]


def user_group(user):
    """Return the name of the user's first group, or a fallback for superusers and anonymous users."""
    try:
        user_group = user.groups.first().name
    except AttributeError:
        user_group = "admin" if user.is_superuser else "anonymous"

    return user_group


def get_study_permission(user, obj):
    """Grant admins and reviewers full access, others access based on study role and access level."""
    try:
        allowed_user_modify = (user == obj.creator) or (user in obj.curators)
        allow_user_get = (
            (user in obj.collaborators) or (obj.access == PUBLIC) or allowed_user_modify
        )
    except TypeError:
        allowed_user_modify = (user == obj.creator) or (user in obj.curators.all())
        allow_user_get = (
            (user in obj.collaborators.all())
            or (obj.access == PUBLIC)
            or allowed_user_modify
        )

    permission_dict = {
        "admin": True,
        "anonymous": (obj.access == PUBLIC),
        "reviewer": True,
        "basic": allow_user_get,
    }
    return permission_dict[user_group(user)]


def get_study_file_permission(user, obj):
    """Grant admins and reviewers full access, others access based on study role and licence.

    Accepts both a Study instance and its elasticsearch dictionary representation.
    """
    allow_user_get = False
    if isinstance(obj, (AttrDict, DictionaryProxy)):
        username = user.username
        curator_usernames = [curator["username"] for curator in obj.curators]
        collaborators_usernames = [
            collaborator["username"] for collaborator in obj.collaborators
        ]
        allowed_user_modify = (username == obj.creator["username"]) or (
            user in curator_usernames
        )
        allow_user_get = (
            (user in collaborators_usernames)
            or (obj.licence == OPEN)
            or allowed_user_modify
        )

    elif isinstance(obj, Study):
        allowed_user_modify = (user == obj.creator) or (user in obj.curators.all())
        allow_user_get = (
            (user in obj.collaborators.all())
            or (obj.licence == OPEN)
            or allowed_user_modify
        )

    permission_dict = {
        "admin": True,
        "anonymous": obj.licence == OPEN,
        "reviewer": True,
        "basic": allow_user_get,
    }
    return permission_dict[user_group(user)]


def anonymous_permissions(request, obj):
    """Grant PUT and safe methods access based on the study's access level."""
    if is_allowed_method(request):
        return get_study_permission(request.user, obj)
    return False


def basic_permission(request, obj):
    """Grant other methods to the study's creator and curators, PUT and safe methods by access level."""
    user = request.user
    try:
        allowed_user_modify = (user == obj.creator) or (user in obj.curators)
    except TypeError:
        allowed_user_modify = (user == obj.creator) or (user in obj.curators.all())

    if is_allowed_method(request):
        return get_study_permission(user, obj)

    return allowed_user_modify


def reviewer_permission(request, obj):
    """Grant PUT and safe methods access based on the study's access level."""
    if is_allowed_method(request):
        return get_study_permission(request.user, obj)
    return False


def admin_permission():
    """Grant full access to admin users."""
    return True
