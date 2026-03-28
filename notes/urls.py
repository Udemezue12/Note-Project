from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import login_view
from .viewsets.auth_viewsets import AuthViewSet
from .viewsets.note_viewsets import NoteViewSet
from .viewsets.sync_notes_views import SyncNotes
from .viewsets.tag_viewsets import TagViewSet
from .viewsets.websockets_test import TestWebSocket
from .views import get_csrf_token

router = DefaultRouter()
router.register('auth', AuthViewSet, basename="auth")
router.register("notes", NoteViewSet, basename='notes')
router.register("tags", TagViewSet, basename='tags')

urlpatterns = [
    path('v1/', include(router.urls)),
    path("v1/sync/", SyncNotes.as_view()),
    path("get_csrfToken/", get_csrf_token),
    path("test-ws/", TestWebSocket.as_view()),
  
   
]

