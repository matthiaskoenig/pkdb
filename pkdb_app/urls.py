from django.conf import settings
from django.urls import path, re_path, include, reverse_lazy
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic.base import RedirectView
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views
from .subjects.views import schema_view
from rest_framework_swagger.views import get_swagger_view


from django.views.decorators.csrf import ensure_csrf_cookie

from .users.views import UserViewSet, UserCreateViewSet
from .studies.views import AuthorsViewSet,InterventionsViewSet,StudiesViewSet


# views in User
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'users', UserCreateViewSet)

# views in studies
router.register('authors',AuthorsViewSet,base_name="authors")
router.register('studies',StudiesViewSet,base_name="study")
router.register('intervention',InterventionsViewSet,base_name="intervention")

# views in subjects
# views in User
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'users', UserCreateViewSet,'user')

# views in studies
router.register(r'authors',AuthorsViewSet)
router.register(r'studies',StudiesViewSet)
router.register(r'intervention',InterventionsViewSet)


schema_view = get_swagger_view(title='PkBD API')





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
