"""
Django URLs
"""
from django.conf.urls import url
from django.urls import path, include
from drf_yasg.views import get_schema_view
from pkdb_app.data.views import DataAnalysisViewSet, SubSetViewSet
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from .views import CustomOpenAPISchemaGenerator
from drf_yasg import openapi

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
router.register("subsets", SubSetViewSet, basename="subsets")

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

router.register("flat/interventions", ElasticInterventionAnalysisViewSet, basename="interventions_analysis")
router.register("flat/groups", GroupCharacteristicaViewSet, basename="groups_analysis")
router.register("flat/individuals", IndividualCharacteristicaViewSet, basename="individuals_analysis")
router.register("flat/output", OutputInterventionViewSet, basename="output_analysis")
router.register("flat/data", DataAnalysisViewSet, basename="data_analysis")



urlpatterns = [
    # api
    path("api/v1/", include(router.urls)),
    path('api/v1/filter/', PKDataView.as_view()),
]
#router.register("pkdata", PKDataView, basename="pkdata")
# FIXME: urls will not work !!!
schema_view = get_schema_view(
   openapi.Info(
    title="PKDB API",
    default_version='v1',
    description="""
    ## Overview
    This is the REST API of PK-DB. The API provides web services for querying data from PKDB. 
     
    The data in PK-DB is structured based on **studies**, with a single study corresponding to a single source of information. In most cases such a study corresponds to a single publication or a single clinical trial. 
    
    A study in PK-DB reports pharmacokinetics information for the subjects under investigation in the study. These subjects are characterised by properties such as their *sex*, *age*, *body weight*, *ethnicity* or *health status*. Depending on the reported information, subject information is stored for **groups** and/or **individuals**. 
    
    A second class of information are the **interventions** which were performed on the subjects. Most of the interventions in pharmacokinetics studies is application of a certain dose of a substance (e.g. 1 mg paracetamol orally as tablet). In addition interventions can also consist of other things changed between the studied subjects or groups, such as food which was applied. 
    
    Finally, pharmacokinetics measurements are performed on the subject. These are often *concentration* measurements in certain tissue of the subject. These can either be single measurements (**outputs**) or time profiles (**time courses**). Additionally, derived pharmacokinetics parameters such as *AUC*, *clearance*, or *half-lives* are commonly reported. Correlations between theses outputs are often shown in form of **scatter** plots.
    
  Meta-information is encoded in the form of an **info nodes** which for a given field encodes meta-data such as description, synonyms, annotations and database cross-references.
    
    The REST API provides endpoints for
    * overview of PK-DB statistics (`statistics`)  
    * searching and filtering of data (`filter`)
    * accessing study information (`studies`)
    * accessing groups (`groups`) and individuals (`individuals`)
    * accessing interventions (`interventions`)
    * accessing outputs (`outputs`) and subsets (`subsets`) 
    * accessing info_nodes information (`info_nodes`)
    
    The public REST API only exposes read serializers. In addition to the API a dedicated python package for the upload and download of data exists. If you are interested in contributing to the database please contact Matthias König.
    """,
    terms_of_service="https://github.com/matthiaskoenig/pkdb/blob/develop/TERMS_OF_USE.md",
    contact=openapi.Contact(email="koenigmx@hu-berlin.de", name="Matthias König"),
    license=openapi.License(name="GNU Lesser General Public License v3 (LGPLv3)"),
    logo={"url": 'http://0.0.0.0:8081/assets/images/logo-PKDB.png', "altText": 'PKDB Logo'}
    ),
   generator_class=CustomOpenAPISchemaGenerator,
   public=False,
   patterns=urlpatterns,
)

urlpatterns = urlpatterns + [
    path("api/v1/update_index/", update_index_study),

    # media files
    url(r'^media/(?P<file>.*)$', serve_protected_document,
        name='serve_protected_document'),

    # authentification
    path('api-token-auth/', ObtainAuthTokenCustom.as_view()),
    path('api-auth/', include("rest_framework.urls", namespace="rest_framework")),

    url(r'^accounts/', include('rest_email_auth.urls')),

    path('verify/?P<key>[-\w]+)', obtain_auth_token),
    path('reset/?P<key>[-\w]+)', obtain_auth_token),

    url(r'^api/v1/swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^api/v1/swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # url(r'^api/v1/redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
