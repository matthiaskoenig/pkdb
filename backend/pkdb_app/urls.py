"""
Django URLs
"""
from django.urls import path, include
from django.conf.urls import url
from django.contrib import admin
from pkdb_app.categorials.views import MeasurementTypeViewSet, MeasurementTypeElasticViewSet
from pkdb_app.outputs.views import ElasticTimecourseViewSet, ElasticOutputViewSet, OutputOptionViewSet, \
    TimecourseOptionViewSet
from pkdb_app.substances.views import SubstanceViewSet, ElasticSubstanceViewSet, SubstanceStatisticsViewSet
from rest_framework.authtoken.views import obtain_auth_token

from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view
from rest_framework.schemas import get_schema_view

from .comments.views import ElasticCommentViewSet, ElasticDescriptionViewSet

from .views import serve_protected_document

from .subjects.views import (
    DataFileViewSet,
    IndividualViewSet,
    CharacteristicaElasticViewSet, CharacteristicaOptionViewSet, GroupViewSet)
from .interventions.views import InterventionOptionViewSet, ElasticInterventionViewSet
from .users.views import UserViewSet, UserCreateViewSet, UserGroupViewSet, ObtainAuthTokenCustom
from .studies.views import (
    ReferencesViewSet,
    StudyViewSet,
    ElasticReferenceViewSet, ElasticStudyViewSet, update_index_study)

from .statistics import StatisticsViewSet, study_pks_view

router = DefaultRouter()

###############################################################################################
# URLs
###############################################################################################

router.register("comments_elastic", ElasticCommentViewSet, base_name="comments_elastic")
router.register("descriptions_elastic", ElasticDescriptionViewSet, base_name="descriptions_elastic")

router.register("references", ReferencesViewSet, base_name="references")
router.register("references_elastic", ElasticReferenceViewSet, base_name="references_elastic")

router.register("measurement_types", MeasurementTypeViewSet, base_name="measurement_types")
router.register("measurement_types_elastic", MeasurementTypeElasticViewSet, base_name="measurement_types_elastic")

router.register("users", UserViewSet, base_name="users")
router.register("users", UserCreateViewSet)
router.register("user_groups", UserGroupViewSet, base_name="user_groups")

router.register("substances", SubstanceViewSet, base_name="substances")
router.register("substances_elastic", ElasticSubstanceViewSet, base_name="substances_elastic")
router.register("substances_statistics", SubstanceStatisticsViewSet, base_name="substances_statistics")

router.register("datafiles", DataFileViewSet, base_name="datafiles")

router.register("studies", StudyViewSet, base_name="studies")
router.register("studies_elastic", ElasticStudyViewSet, base_name="studies_elastic")

router.register("statistics", StatisticsViewSet, base_name="statistics")


###############################################################################################
# Read URLs
###############################################################################################

router.register("individuals_elastic", IndividualViewSet, base_name="individuals_elastic")
router.register("groups_elastic", GroupViewSet, base_name="groups_elastic")
router.register("characteristica_elastic", CharacteristicaElasticViewSet, base_name="characteristica_elastic")
router.register("interventions_elastic", ElasticInterventionViewSet, base_name="interventions_elastic")
router.register("timecourses_elastic", ElasticTimecourseViewSet, base_name="timecourses_elastic")
router.register("outputs_elastic", ElasticOutputViewSet, base_name="outputs_elastic")

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
#schema_view = get_schema_view(title="PKDB API")


urlpatterns = [
    # authentication
    #(r'^accounts_old/', include('allauth.urls')),
    url(r'^accounts/', include('rest_email_auth.urls')),

    # admin
    path("admin/", admin.site.urls),
    # api
    path(r"api/v1/", include(router.urls)),
    path("api/v1/study_pks/", study_pks_view),
    path("api/v1/update_index/", update_index_study),
    path('api-token-auth/', ObtainAuthTokenCustom.as_view()),
    path('verify/?P<key>[-\w]+)', obtain_auth_token),
    path('reset/?P<key>[-\w]+)', obtain_auth_token),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"api", schema_view, name="api"),
    url(r'^media/(?P<file>.*)$', serve_protected_document, name='serve_protected_document'),

    # for debugging
    # url(r'test/', views.test_500_view, name='test'),
    # url(r'test/', views.test_view, name='test'),
    # the 'api-root' from django rest-frameworks default router
    # http://www.django-rest-framework.org/api-guide/routers/#defaultrouter
    # re_path(r'^$', RedirectView.as_view(url=reverse_lazy('api-root'), permanent=False)),
] #+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
