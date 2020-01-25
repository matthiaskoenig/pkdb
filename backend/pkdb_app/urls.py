"""
Django URLs
"""
from django.urls import path, include
from django.conf.urls import url

from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter


from .views import serve_protected_document
from .statistics import StatisticsViewSet, study_pks_view
from pkdb_app.categorials.views import MeasurementTypeViewSet, \
    MeasurementTypeElasticViewSet, TissueViewSet, \
    ApplicationViewSet, FormViewSet, RouteViewSet
from pkdb_app.outputs.views import ElasticTimecourseViewSet, \
    ElasticOutputViewSet,  OutputInterventionViewSet, \
    TimecourseInterventionViewSet
from pkdb_app.substances.views import SubstanceViewSet, ElasticSubstanceViewSet

from .subjects.views import (
    DataFileViewSet,
    IndividualViewSet,
    GroupViewSet,
    GroupCharacteristicaViewSet,
    IndividualCharacteristicaViewSet
)
from .interventions.views import (
    ElasticInterventionViewSet,
    ElasticInterventionAnalysisViewSet
)
from .users.views import (
    UserViewSet,
    UserCreateViewSet,
    UserGroupViewSet,
    ObtainAuthTokenCustom
)
from .studies.views import (
    ReferencesViewSet,
    StudyViewSet,
    ElasticReferenceViewSet,
    ElasticStudyViewSet,
    update_index_study
)

router = DefaultRouter()

# -----------------------------------------------------------------------------
# Misc URLs
# -----------------------------------------------------------------------------
router.register("statistics", StatisticsViewSet, basename="statistics")

# -----------------------------------------------------------------------------
# Elastic URLs
# -----------------------------------------------------------------------------
router.register("studies", ElasticStudyViewSet, basename="studies")
router.register("references", ElasticReferenceViewSet, basename="references")

router.register("groups", GroupViewSet, basename="groups_elastic")
router.register("individuals", IndividualViewSet, basename="individuals")
router.register("interventions", ElasticInterventionViewSet, basename="interventions")
router.register("outputs", ElasticOutputViewSet, basename="outputs")
router.register("timecourses", ElasticTimecourseViewSet, basename="timecourses")

router.register("measurement_types", MeasurementTypeElasticViewSet, basename="measurement_types")
router.register("substances", ElasticSubstanceViewSet, basename="substances")

# -----------------------------------------------------------------------------
# Django URLs
# -----------------------------------------------------------------------------
# django (mainly write endpoints)
router.register("_studies", StudyViewSet, basename="_studies")
router.register("_references", ReferencesViewSet, basename="_references")
router.register("_datafiles", DataFileViewSet, basename="_datafiles")
router.register("_users", UserViewSet, basename="_users")
router.register("_users", UserCreateViewSet, basename="_users")
router.register("_user_groups", UserGroupViewSet, basename="_user_groups")

router.register("_measurement_types", MeasurementTypeViewSet, basename="_measurement_types") # django
router.register("_substances", SubstanceViewSet, basename="_substances")  # django
router.register("_tissues", TissueViewSet, basename="_tissues")  # django
router.register("_applications", ApplicationViewSet, basename="_applications")  # django
router.register("_forms", FormViewSet, basename="_forms")  # django
router.register("_routes", RouteViewSet, basename="_routes")  # django


# TODO: remove #########################################
#router.register("comments_elastic", ElasticCommentViewSet, basename="comments_elastic")
#router.register("descriptions_elastic", ElasticDescriptionViewSet, basename="descriptions_elastic")
#router.register("substances_statistics", SubstanceStatisticsViewSet, basename="substances_statistics")

# Options
#router.register("characteristica_options", CharacteristicaOptionViewSet, basename="characteristica_option")
#router.register("intervention_options", InterventionOptionViewSet, basename="intervention_option")
#router.register("output_options", OutputOptionViewSet, basename="output_option")
#router.register("timecourse_options", TimecourseOptionViewSet, basename="timecourse_option")

# todo: remove -> this is for pkdb_analysis
router.register("interventions_analysis", ElasticInterventionAnalysisViewSet, basename="interventions_analysis")
router.register("characteristica_groups", GroupCharacteristicaViewSet, basename="characteristica_groups")
router.register("characteristica_individuals", IndividualCharacteristicaViewSet, basename="characteristica_individuals")
router.register("output_intervention", OutputInterventionViewSet, basename="output_intervention")
router.register("timecourse_intervention", TimecourseInterventionViewSet, basename="timecourse_intervention")


urlpatterns = [

    # api
    path("api/v1/", include(router.urls)),
    path("api/v1/study_pks/", study_pks_view),
    path("api/v1/update_index/", update_index_study),

    # media files
    url(r'^media/(?P<file>.*)$', serve_protected_document,
        name='serve_protected_document'),

    # authentification
    path('api-token-auth/', ObtainAuthTokenCustom.as_view()),
    url(r'^accounts/', include('rest_email_auth.urls')),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path('verify/?P<key>[-\w]+)', obtain_auth_token),
    path('reset/?P<key>[-\w]+)', obtain_auth_token),
]
