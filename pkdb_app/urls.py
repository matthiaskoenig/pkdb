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

'''
from rest_framework_swagger import renderers
from rest_framework import exceptions
from rest_framework.permissions import AllowAny
from rest_framework.renderers import CoreJSONRenderer
from rest_framework.response import Response
from rest_framework.schemas import SchemaGenerator
from rest_framework.views import APIView
'''


from .subjects.views import DataFileViewSet
from .interventions.views import SubstancesViewSet
from .users.views import UserViewSet, UserCreateViewSet
from .studies.views import AuthorsViewSet, ReferencesViewSet, StudyViewSet
#from .subjects.views import GroupsViewSet, CharacteristicValuesViewSet


from .statistics import StatisticsViewSet
from . import views

# views in User
router = DefaultRouter()

router.register(r'users', UserViewSet)
router.register(r'users', UserCreateViewSet)

router.register('substances', SubstancesViewSet, base_name="substances")
router.register('datafiles', DataFileViewSet, base_name="datafiles")

# views in studies
router.register('authors', AuthorsViewSet, base_name="authors")
router.register('references', ReferencesViewSet, base_name="references")

router.register('studies', StudyViewSet, base_name="studies")
router.register('statistics', StatisticsViewSet, base_name="statistics")


# router.register('groups', GroupsViewSet, base_name="groups")
# router.register('characteristic_values', CharacteristicValuesViewSet, base_name="characteristic_values")
# router.register('intervention',InterventionsViewSet,base_name="intervention")


'''
class JSONOpenAPIRenderer(renderers.OpenAPIRenderer):
    media_type = 'application/json'

def get_swagger_view(title=None, url=None, patterns=None, urlconf=None):
    """
    Returns schema view which renders Swagger/OpenAPI.
    Custom get swagger view.
    see https://github.com/marcgibbons/django-rest-swagger/issues/701
    """
    class SwaggerSchemaView(APIView):
        _ignore_model_permissions = True
        exclude_from_schema = True
        permission_classes = [AllowAny]
        renderer_classes = [
            CoreJSONRenderer,
            JSONOpenAPIRenderer,
            renderers.OpenAPIRenderer,
            renderers.SwaggerUIRenderer
        ]

        def get(self, request):
            generator = SchemaGenerator(
                title=title,
                url=url,
                patterns=patterns,
                urlconf=urlconf
            )
            schema = generator.get_schema(request=request)

            if not schema:
                raise exceptions.ValidationError(
                    'The schema generator did not return a schema Document'
                )

            return Response(schema)

    return SwaggerSchemaView.as_view()
'''

schema_view = get_swagger_view(title='PKDB API')


urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^$', views.about_view, name='index'),
    url(r'api', schema_view, name='api'),
    path(r'^api/v1/', include(router.urls)),
    # path('api-token-auth/', views.obtain_auth_token),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # the 'api-root' from django rest-frameworks default router
    # http://www.django-rest-framework.org/api-guide/routers/#defaultrouter
    #re_path(r'^$', RedirectView.as_view(url=reverse_lazy('api-root'), permanent=False)),



] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
