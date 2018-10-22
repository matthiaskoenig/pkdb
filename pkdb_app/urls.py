"""
Django URLs
"""
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
    CharacteristicaReadViewSet,
    IndividualReadViewSet,
    GroupSetReadViewSet,
    IndividualSetReadViewSet,
    CharacteristicaExReadViewSet, IndividualExReadViewSet, IndividualViewSet,
    CharacteristicaViewSet, CharacteristicaOptionViewSet, GroupViewSet)
from .interventions.views import (
    SubstanceViewSet,
    SubstanceReadViewSet,
    InterventionSetReadViewSet,
    OutputSetReadViewSet,
    InterventionReadViewSet,
    OutputReadViewSet,
    TimecourseReadViewSet,
    InterventionExReadViewSet, OutputExReadViewSet, TimecourseExReadViewSet, InterventionOptionViewSet,
    OutputOptionViewSet, TimecourseOptionViewSet, ElasticSubstanceViewSet, ElasticInterventionViewSet,
    ElasticOutputViewSet, ElasticTimecourseViewSet)
from .users.views import UserViewSet, UserCreateViewSet, UserReadViewSet
from .studies.views import (
    ReferencesViewSet,
    StudyViewSet,
    StudyReadViewSet,

    KeywordViewSet,
    KeywordReadViewSet,
    ElasticReferenceViewSet, ElasticStudyViewSet)

# from .subjects.views import GroupsViewSet, CharacteristicValuesViewSet
from .statistics import StatisticsViewSet, StatisticsDataViewSet
from . import views


# views in User
router = DefaultRouter()
router.register("references", ReferencesViewSet, base_name="references")
router.register("references_elastic", ElasticReferenceViewSet, base_name="references_elastic")



router.register(r"users", UserViewSet, base_name="users")

router.register(r"users", UserCreateViewSet)

router.register("substances", SubstanceViewSet, base_name="substances")
router.register("keywords", KeywordViewSet, base_name="keywords")

router.register("datafiles", DataFileViewSet, base_name="datafiles")
router.register("datafiles_read", DataFileReadViewSet, base_name="datafiles_read")




router.register("studies", StudyViewSet, base_name="studies")
router.register("studies_elastic", ElasticStudyViewSet, base_name="studies_elastic")


router.register("statistics", StatisticsViewSet, base_name="statistics")
router.register("statistics_data", StatisticsDataViewSet, base_name="statistics_data")


###############################################################################################
# Read URLs
###############################################################################################

router.register("studies_read", StudyReadViewSet, base_name="studies_read")


router.register(r"users_read", UserReadViewSet, base_name="users_read")


router.register("substances_read", SubstanceReadViewSet, base_name="substances_read")
router.register("substances_elastic", ElasticSubstanceViewSet, base_name="substances_elastic")

router.register("keywords_read", KeywordReadViewSet, base_name="keywords_read")

router.register(
    "descriptions_read", DescriptionReadViewSet, base_name="descriptions_read"
)
router.register(
    "comments_read", CommentReadViewSet, base_name="comments_read"
)

router.register("groupsets_read", GroupSetReadViewSet, base_name="groupsets_read")

router.register(
    "individualsets_read", IndividualSetReadViewSet, base_name="individualsets_read"
)
router.register("individuals_read", IndividualReadViewSet, base_name="individuals_read")
router.register("individuals_elastic", IndividualViewSet, base_name="individuals_elastic")
router.register("groups_elastic", GroupViewSet, base_name="groups_elastic")

router.register("characteristica_elastic", CharacteristicaViewSet, base_name="characteristica_elastic")


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
    "interventions_elastic", ElasticInterventionViewSet, base_name="interventions_elastic"
)
router.register(
    "timecourses_elastic", ElasticTimecourseViewSet, base_name="timecourses_elastic"
)
router.register(
    "outputs_elastic", ElasticOutputViewSet, base_name="outputs_elastic"
)
router.register(
    "interventionexs_read", InterventionExReadViewSet, base_name="interventionexs_read"
)
router.register("outputset_read", OutputSetReadViewSet, base_name="outputsets_read")
router.register("outputs_read", OutputReadViewSet, base_name="outputs_read")
router.register("outputexs_read", OutputExReadViewSet, base_name="outputexs_read")

router.register("timecourses_read", TimecourseReadViewSet, base_name="timecourses_read")
router.register("timecourseexs_read", TimecourseExReadViewSet, base_name="timecourseexs_read")

# Options
router.register(
    "characteristica_options", CharacteristicaOptionViewSet, base_name="characteristica_option"
)
router.register(
    "intervention_options", InterventionOptionViewSet, base_name="intervention_option"
)
router.register(
    "output_options", OutputOptionViewSet, base_name="output_option"
)
router.register(
    "timecourse_options", TimecourseOptionViewSet, base_name="timecourse_option"
)
schema_view = get_swagger_view(title="PKDB API")


urlpatterns = [
    # authentication
    url(r'^accounts/', include('allauth.urls')),

    # admin
    path("admin/", admin.site.urls),

    # api
    path(r"api/v1/", include(router.urls)),
    path('api-token-auth/', obtain_auth_token),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"api", schema_view, name="api"),

    # for debugging
    url(r'atest/', views.test_500_view, name='test'),

    # the 'api-root' from django rest-frameworks default router
    # http://www.django-rest-framework.org/api-guide/routers/#defaultrouter
    # re_path(r'^$', RedirectView.as_view(url=reverse_lazy('api-root'), permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
