from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ..cache_deps import cache_deps
from ..models import Tag
from ..serializers.note_serializers import TagSerializer


class TagViewSet(ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
 

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        user = self.request.user
        return (
            Tag.objects.filter(user=user, is_deleted=False)
            .select_related("user")
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        user = request.user
        cache_key = f"tags_user_{user.id}"

        data = cache_deps.get_from_cache(cache_key)

        if not data:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

            cache_deps.set_from_cache(cache_key, data, timeout=60 * 5)

        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        note_id = kwargs.get("pk")

        cache_key = f"tag_{user.id}_{note_id}"

        data = cache_deps.get_from_cache(cache_key)

        if not data:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            data = serializer.data

            cache_deps.set_from_cache(cache_key, data, timeout=60 * 5)

        return Response(data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

        cache_deps.delete_from_cache(f"tags_user_{self.request.user.id}")

    def perform_update(self, serializer):
        note = self.get_object()

        if note.user != self.request.user:
            raise PermissionDenied("You cannot edit this tag")

        note = serializer.save(version=note.version + 1)

        cache_deps.delete_many_from_cache(
            f"tags_user_{self.request.user.id}", f"tag_{self.request.user.id}_{note.id}"
        )

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied("You cannot delete this tag")

        instance.is_deleted = True
        instance.save()

        cache_deps.delete_many_from_cache(
            f"tags_user_{self.request.user.id}",
            f"tag_{self.request.user.id}_{instance.id}",
        )
