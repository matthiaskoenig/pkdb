"""
Django URLs
"""
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm

from django.conf import settings
from django.urls import path, include
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework.authtoken.views import obtain_auth_token

from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view

from pkdb_app.comments.views import DescriptionReadViewSet, CommentReadViewSet



from .subjects.views import (
    DataFileViewSet,
    DataFileReadViewSet,
    GroupReadViewSet,
    CharacteristicaReadViewSet,
    IndividualReadViewSet,
    GroupSetReadViewSet,
    IndividualSetReadViewSet,
    CharacteristicaExReadViewSet, GroupExReadViewSet, IndividualExReadViewSet)
from .interventions.views import (
    SubstanceViewSet,
    SubstanceReadViewSet,
    InterventionSetReadViewSet,
    OutputSetReadViewSet,
    InterventionReadViewSet,
    OutputReadViewSet,
    TimecourseReadViewSet,
    InterventionExReadViewSet, OutputExReadViewSet, TimecourseExReadViewSet)
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
router.register(
    "comments_read", CommentReadViewSet, base_name="comments_read"
)

router.register("groupsets_read", GroupSetReadViewSet, base_name="groupsets_read")
router.register("groups_read", GroupReadViewSet, base_name="groups_read")
router.register("groupexs_read", GroupExReadViewSet, base_name="groupexs_read")

router.register(
    "individualsets_read", IndividualSetReadViewSet, base_name="individualsets_read"
)
router.register("individuals_read", IndividualReadViewSet, base_name="individuals_read")
router.register("individualexs_read", IndividualExReadViewSet, base_name="individualexs_read")

router.register(
    "characteristica_read", CharacteristicaReadViewSet, base_name="characteristica_read"
)
router.register(
    "characteristicaex_read", CharacteristicaExReadViewSet, base_name="characteristicaex_read"
)

router.register(
    "interventionsets_read",
    InterventionSetReadViewSet,
    base_name="interventionsets_read",
)
router.register(
    "interventions_read", InterventionReadViewSet, base_name="interventions_read"
)
router.register(
    "interventionexs_read", InterventionExReadViewSet, base_name="interventionexs_read"
)
router.register("outputset_read", OutputSetReadViewSet, base_name="outputsets_read")
router.register("outputs_read", OutputReadViewSet, base_name="outputs_read")
router.register("outputexs_read", OutputExReadViewSet, base_name="outputexs_read")

router.register("timecourses_read", TimecourseReadViewSet, base_name="timecourses_read")
router.register("timecourseexs_read", TimecourseExReadViewSet, base_name="timecourseexs_read")


schema_view = get_swagger_view(title="PKDB API")


urlpatterns = [
    path("admin/", admin.site.urls),
    path(r"api/v1/", include(router.urls)),
    path('api-token-auth/', obtain_auth_token),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"api", schema_view, name="api"),

    # authentication
    url(r'^accounts/', include('allauth.urls')),

    # the 'api-root' from django rest-frameworks default router
    # http://www.django-rest-framework.org/api-guide/routers/#defaultrouter
    # re_path(r'^$', RedirectView.as_view(url=reverse_lazy('api-root'), permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
