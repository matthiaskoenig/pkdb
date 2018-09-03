"""
Django URLs
"""
from django.conf import settings
from django.urls import path, include
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin

from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view

from pkdb_app.comments.views import DescriptionReadViewSet

"""
from rest_framework_swagger import renderers
from rest_framework import exceptions
from rest_framework.permissions import AllowAny
from rest_framework.renderers import CoreJSONRenderer
from rest_framework.response import Response
from rest_framework.schemas import SchemaGenerator
from rest_framework.views import APIView
"""


from .subjects.views import (
    DataFileViewSet,
    DataFileReadViewSet,
    GroupReadViewSet,
    CharacteristicaReadViewSet,
    IndividualReadViewSet,
    GroupSetReadViewSet,
    IndividualSetReadViewSet,
)
from .interventions.views import (
    SubstanceViewSet,
    SubstanceReadViewSet,
    InterventionSetReadViewSet,
    OutputSetReadViewSet,
    InterventionReadViewSet,
    OutputReadViewSet,
    TimecourseReadViewSet,
)
from .users.views import UserViewSet, UserCreateViewSet, UserReadViewSet
from .studies.views import (
    AuthorsViewSet,
    ReferencesViewSet,
    StudyViewSet,
    StudyReadViewSet,
    AuthorsReadViewSet,
    ReferencesReadViewSet,
    KeywordViewSet,
    KeywordReadViewSet,
)

# from .subjects.views import GroupsViewSet, CharacteristicValuesViewSet


from .statistics import StatisticsViewSet
from . import views

# views in User
router = DefaultRouter()

router.register(r"users", UserViewSet, base_name="users")

router.register(r"users", UserCreateViewSet)

router.register("substances", SubstanceViewSet, base_name="substances")
router.register("keywords", KeywordViewSet, base_name="keywords")

router.register("datafiles", DataFileViewSet, base_name="datafiles")
router.register("datafiles_read", DataFileReadViewSet, base_name="datafiles_read")

# views in studies
router.register("authors", AuthorsViewSet, base_name="authors")

router.register("references", ReferencesViewSet, base_name="references")


router.register("studies", StudyViewSet, base_name="studies")

router.register("statistics", StatisticsViewSet, base_name="statistics")


###############################################################################################
# Read URLs
###############################################################################################
router.register("studies_read", StudyReadViewSet, base_name="studies_read")
router.register("references_read", ReferencesReadViewSet, base_name="references_read")
router.register("authors_read", AuthorsReadViewSet, base_name="authors_read")

router.register(r"users_read", UserReadViewSet, base_name="users_read")


router.register("substances_read", SubstanceReadViewSet, base_name="substances_read")
router.register("keywords_read", KeywordReadViewSet, base_name="keywords_read")

router.register(
    "descriptions_read", DescriptionReadViewSet, base_name="descriptions_read"
)


router.register("groupsets_read", GroupSetReadViewSet, base_name="groupsets_read")
router.register("groups_read", GroupReadViewSet, base_name="groups_read")
router.register(
    "individualsets_read", IndividualSetReadViewSet, base_name="individualsets_read"
)
router.register("individuals_read", IndividualReadViewSet, base_name="individuals_read")
router.register(
    "characteristica_read", CharacteristicaReadViewSet, base_name="characteristica_read"
)

router.register(
    "interventionsets_read",
    InterventionSetReadViewSet,
    base_name="interventionsets_read",
)
router.register(
    "interventions_read", InterventionReadViewSet, base_name="interventions_read"
)

router.register("outputset_read", OutputSetReadViewSet, base_name="outputsets_read")
router.register("outputs_read", OutputReadViewSet, base_name="outputs_read")
router.register("timecourses_read", TimecourseReadViewSet, base_name="timecourses_read")


schema_view = get_swagger_view(title="PKDB API")


urlpatterns = [
    path("admin/", admin.site.urls),
    path(r"api/v1/", include(router.urls)),
    # path('api-token-auth/', views.obtain_auth_token),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"api", schema_view, name="api"),
    # url(r'/', views.about_view, name='index'),
    # the 'api-root' from django rest-frameworks default router
    # http://www.django-rest-framework.org/api-guide/routers/#defaultrouter
    # re_path(r'^$', RedirectView.as_view(url=reverse_lazy('api-root'), permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [url(r"^__debug__/", include(debug_toolbar.urls))] + urlpatterns
