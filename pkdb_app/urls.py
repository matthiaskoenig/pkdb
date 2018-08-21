"""
Django URLs
"""
from django.urls import path
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from rest_framework_swagger.views import get_swagger_view
from django.conf import settings
from django.conf.urls import include, url

from pkdb_app.subjects.views import DataFileViewSet
from .interventions.views import SubstancesViewSet
from .users.views import UserViewSet, UserCreateViewSet
from .studies.views import AuthorsViewSet, ReferencesViewSet, StudyViewSet

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

# schema
schema_view = get_swagger_view(title='PKDB API')


# url patterns
urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^$', schema_view),
    path('api/v1/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
