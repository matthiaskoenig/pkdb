from pkdb_app.studies.models import OPEN
from pkdb_app.users.models import PUBLIC
from pkdb_app.users.serializers import UserSerializer
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

        # for reference model
        if obj.study.first():
            allowed_user = (request.user == obj.study.first().creator) or (request.user in obj.study.first().curators.all())
        else:
            allowed_user = True


        return request.user.is_staff or allowed_user

class StudyPermission(permissions.BasePermission):


    def has_object_permission(self, request, view, obj):
        if hasattr(obj,"study"):
            if obj.study:
                obj = obj.study.first()

        return study_permissions(request,obj)


def study_permissions(request, obj):
    study_permissions = {"admin": admin_permission(),
                         "basic": basic_permission(request, obj),
                         "reviewer": reviewer_permission(request,obj),
                         "anonymous": anonymous_permissions(request, obj)}


    return study_permissions[user_group(request.user)]

def user_group(user):

    try:
        user_group = user.groups.first().name
    except AttributeError:

        if user.is_superuser:
            user_group = "admin"

        else:
            user_group = "anonymous"

    return user_group

def get_study_permission(user,obj):
    try:
        allowed_user_modify = (user == obj.creator) or (user in obj.curators)
        allow_user_get =(user in obj.collaborators) or  (obj.access == PUBLIC) or allowed_user_modify
    except TypeError:
        allowed_user_modify = (user == obj.creator) or (user in obj.curators.all())
        allow_user_get = (user in obj.collaborators.all()) or (obj.access == PUBLIC) or allowed_user_modify

    permission_dict =  {
        "admin": True,
        "anonymous":(obj.access == PUBLIC),
        "reviewer": True,
        "basic": allow_user_get
     }
    return permission_dict[user_group(user)]


def get_study_file_permission(user,obj):
    try:
        username = user.username
        curator_usernames = [curator["username"] for curator in obj.curators]
        collaborators_usernames = [collaborator["username"] for collaborator in obj.collaborators]

        allowed_user_modify = (username == obj.creator["username"]) or (user in curator_usernames)
        allow_user_get =(user in collaborators_usernames) or (obj.licence == OPEN) or allowed_user_modify


        print(user)
        print(allow_user_get)
    except TypeError:
        allowed_user_modify = (user == obj.creator) or (user in obj.curators.all())
        allow_user_get = (user in obj.collaborators.all()) or (obj.licence == OPEN) or allowed_user_modify

    permission_dict =  {
        "admin": True,
        "anonymous":(obj.licence == OPEN),
        "reviewer": True,
        "basic": allow_user_get
     }

    return permission_dict[user_group(user)]


def anonymous_permissions(request,obj):
    if is_allowed_method(request):
        return get_study_permission(request.user, obj)
    return False


def basic_permission(request, obj):

    user = request.user
    try:
        allowed_user_modify = (user == obj.creator) or (user in obj.curators)
    except TypeError:
        allowed_user_modify = (user == obj.creator) or (user in obj.curators.all())

    if is_allowed_method(request):
        return get_study_permission(user, obj)


    return allowed_user_modify


def reviewer_permission(request,obj):

    if is_allowed_method(request):
        return get_study_permission(request.user, obj)
    else:
        return False


def admin_permission():
    return True



