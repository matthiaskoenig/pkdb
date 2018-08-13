from django.conf import settings
from django.urls import path, include
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view
from django.conf import settings
from django.conf.urls import include, url

from .interventions.views import SubstancesViewSet, DataFileViewSet
from .users.views import UserViewSet, UserCreateViewSet
from .studies.views import AuthorsViewSet, ReferencesViewSet, StudyViewSet
#from .subjects.views import GroupsViewSet,CharacteristicValuesViewSet

# views in User
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'users', UserCreateViewSet)

router.register('substances', SubstancesViewSet, base_name="substances")
router.register('datafiles', DataFileViewSet, base_name="datafiles")

# views in studies
router.register('authors',AuthorsViewSet,base_name="authors")
router.register('references', ReferencesViewSet, base_name="references")

router.register('studies',StudyViewSet, base_name="studies")

#router.register('groups', GroupsViewSet, base_name="groups")
#router.register('characteristic_values', CharacteristicValuesViewSet, base_name="characteristic_values")

#router.register('intervention',InterventionsViewSet,base_name="intervention")

schema_view = get_swagger_view(title='PKDB API')





urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^$', schema_view),
    path('api/v1/', include(router.urls)),
    #path('api-token-auth/', views.obtain_auth_token),
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