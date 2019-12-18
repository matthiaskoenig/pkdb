"""
Django URLs
"""
from django.urls import path, include
from django.conf.urls import url
from django.contrib import admin
from pkdb_app.categorials.views import MeasurementTypeViewSet, MeasurementTypeElasticViewSet, TissueViewSet, \
    ApplicationViewSet, FormViewSet, RouteViewSet
from pkdb_app.outputs.views import ElasticTimecourseViewSet, ElasticOutputViewSet, OutputOptionViewSet, \
    TimecourseOptionViewSet, OutputInterventionViewSet, \
    TimecourseInterventionViewSet
from pkdb_app.substances.views import SubstanceViewSet, ElasticSubstanceViewSet, SubstanceStatisticsViewSet
from rest_framework.authtoken.views import obtain_auth_token

from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view

from .comments.views import ElasticCommentViewSet, ElasticDescriptionViewSet

from .views import serve_protected_document

from .subjects.views import (
    DataFileViewSet,
    IndividualViewSet,
    CharacteristicaElasticViewSet, CharacteristicaOptionViewSet, GroupViewSet, GroupCharacteristicaViewSet,
    IndividualCharacteristicaViewSet)
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

router.register("comments_elastic", ElasticCommentViewSet, basename="comments_elastic")
router.register("descriptions_elastic", ElasticDescriptionViewSet, basename="descriptions_elastic")

router.register("references", ReferencesViewSet, basename="references")
router.register("references_elastic", ElasticReferenceViewSet, basename="references_elastic")

router.register("measurement_types", MeasurementTypeViewSet, basename="measurement_types")
router.register("measurement_types_elastic", MeasurementTypeElasticViewSet, basename="measurement_types_elastic")

router.register("tissues", TissueViewSet, basename="tissues")
router.register("applications", ApplicationViewSet, basename="applications")
router.register("forms", FormViewSet, basename="forms")
router.register("routes", RouteViewSet, basename="routes")

router.register("users", UserViewSet, basename="users")
router.register("users", UserCreateViewSet)
router.register("user_groups", UserGroupViewSet, basename="user_groups")

router.register("substances", SubstanceViewSet, basename="substances")
router.register("substances_elastic", ElasticSubstanceViewSet, basename="substances_elastic")
router.register("substances_statistics", SubstanceStatisticsViewSet, basename="substances_statistics")

router.register("datafiles", DataFileViewSet, basename="datafiles")

router.register("studies", StudyViewSet, basename="studies")
router.register("studies_elastic", ElasticStudyViewSet, basename="studies_elastic")

router.register("statistics", StatisticsViewSet, basename="statistics")

###############################################################################################
# Read URLs
###############################################################################################

router.register("individuals_elastic", IndividualViewSet, basename="individuals_elastic")
router.register("groups_elastic", GroupViewSet, basename="groups_elastic")
router.register("characteristica_elastic", CharacteristicaElasticViewSet, basename="characteristica_elastic")

router.register("characteristica_groups", GroupCharacteristicaViewSet, basename="characteristica_groups")
router.register("characteristica_individuals", IndividualCharacteristicaViewSet,
                basename="characteristica_individuals")

router.register("interventions_elastic", ElasticInterventionViewSet, basename="interventions_elastic")
router.register("timecourses_elastic", ElasticTimecourseViewSet, basename="timecourses_elastic")
router.register("outputs_elastic", ElasticOutputViewSet, basename="outputs_elastic")
router.register("output_intervention", OutputInterventionViewSet, basename="output_intervention")
router.register("timecourse_intervention", TimecourseInterventionViewSet, basename="timecourse_intervention")

# Options
router.register(
    "characteristica_options", CharacteristicaOptionViewSet, basename="characteristica_option"
)
router.register(
    "intervention_options", InterventionOptionViewSet, basename="intervention_option"
)
router.register(
    "output_options", OutputOptionViewSet, basename="output_option"
)
router.register(
    "timecourse_options", TimecourseOptionViewSet, basename="timecourse_option"
)

schema_view = get_swagger_view(title="PKDB API")

urlpatterns = [
    # authentication
    # (r'^accounts_old/', include('allauth.urls')),
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
]  # + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
