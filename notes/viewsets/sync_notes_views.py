from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..cache_deps import cache_deps
from ..crud_deps import crud_actions
from ..models import Note
from ..serializers.note_serializers import NoteSerializer
from ..tasks.sync_all_notes_tasks import sync_all_notes_tasks


class SyncNotes(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        last_sync = request.query_params.get("last_sync")
        queryset = crud_actions.get_single_related_without_filter(
            model=Note,
            select_related=["user", "tag"]
        )

        if last_sync:
            parsed = parse_datetime(last_sync)
            if parsed:
                queryset = queryset.filter(updated_at__gt=parsed)

        return Response(
            {"notes": NoteSerializer(
                queryset, many=True).data, "server_time": now()}
        )

    def post(self, request):
        user_id = request.user.id
        print(f"user:{user_id}")
        cache_key = f"sync_running_user_{user_id}"

        if cache_deps.get_from_cache(cache_key):
            return Response({"message": "Sync already running"})

        cache_deps.set_from_cache(cache_key, True, timeout=15)

        sync_all_notes_tasks.delay(str(user_id))

        return Response({"message": "Sync started"})
