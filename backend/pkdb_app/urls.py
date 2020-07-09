"""
Django URLs
"""
from django.conf.urls import url
from django.urls import path, include
from pkdb_app.data.views import DataAnalysisViewSet
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from .statistics import (
    StatisticsViewSet,
)

from .info_nodes.views import (
    InfoNodeViewSet,
    InfoNodeElasticViewSet,
)
from .outputs.views import (
    ElasticOutputViewSet,
    OutputInterventionViewSet)
from .interventions.views import (
    ElasticInterventionViewSet,
    ElasticInterventionAnalysisViewSet
)
from .studies.views import (
    ReferencesViewSet,
    StudyViewSet,
    ElasticReferenceViewSet,
    ElasticStudyViewSet,
    update_index_study, PKDataView,
)
from .subjects.views import (
    DataFileViewSet,
    IndividualViewSet,
    GroupViewSet,
    GroupCharacteristicaViewSet,
    IndividualCharacteristicaViewSet,
)
from .users.views import (
    UserViewSet,
    UserCreateViewSet,
    UserGroupViewSet,
    ObtainAuthTokenCustom,
)
from .views import serve_protected_document


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
router.register("info_nodes", InfoNodeElasticViewSet, basename="info_nodes")

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

router.register('_info_nodes', InfoNodeViewSet, basename="_info_nodes")  # django

router.register("interventions_analysis", ElasticInterventionAnalysisViewSet, basename="interventions_analysis")
router.register("groups_analysis", GroupCharacteristicaViewSet, basename="groups_analysis")
router.register("individuals_analysis", IndividualCharacteristicaViewSet, basename="individuals_analysis")
router.register("output_analysis", OutputInterventionViewSet, basename="output_analysis")
router.register("data_analysis", DataAnalysisViewSet, basename="data_analysis")
#router.register("pkdata", PKDataView, basename="pkdata")


urlpattern_views = []
urlpatterns = [
    # authentification
    path('api-token-auth/', ObtainAuthTokenCustom.as_view()),
    path('api-auth/', include("rest_framework.urls", namespace="rest_framework")),

    # api
    path("api/v1/", include(router.urls)),
    path('api/v1/pkdata/', PKDataView.as_view()),
    path("api/v1/update_index/", update_index_study),

    # media files
    url(r'^media/(?P<file>.*)$', serve_protected_document,
        name='serve_protected_document'),

    url(r'^accounts/', include('rest_email_auth.urls')),

    path('verify/?P<key>[-\w]+)', obtain_auth_token),
    path('reset/?P<key>[-\w]+)', obtain_auth_token),
]
