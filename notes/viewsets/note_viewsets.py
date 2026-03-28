import uuid

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.viewsets import ModelViewSet

from ..cache_deps import cache_deps
from ..crud_deps import crud_actions
from ..models import Note, Tag
from ..serializers.note_serializers import NoteSerializer
from ..sync_helper import add_to_sync_queue
from ..webscokets.note_websocket_update import send_note_update


class NoteViewSet(ModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["title", "content"]

    def get_queryset(self):
        user = self.request.user
        return (
            Note.objects.filter(user=user, is_deleted=False)
            .select_related("user", "tag")
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        user = request.user
        json_cache_key = f"notes_user_json_{user.id}"
        htmx_cache_key = f"notes_user_html_{user.id}"

        is_htmx = request.headers.get("HX-Request")
        queryset = self.get_queryset()

        if is_htmx:
            html = cache_deps.get_from_cache(htmx_cache_key)
            if not html:
                html = render_to_string(
                    "partials/note_list.html", {"notes": queryset}, request=request
                )
                cache_deps.set_from_cache(htmx_cache_key, html, 60 * 2)

            return HttpResponse(html)
        data = cache_deps.get_from_cache(json_cache_key)

        if not data:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

            cache_deps.set_from_cache(json_cache_key, data, timeout=60 * 5)

        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        note_id = kwargs.get("pk")
        is_htmx = request.headers.get("HX-Request")
        htmx_cache_key = f"note_html_{user.id}_{note_id}"
        json_cache_key = f"note_json_{user.id}_{note_id}"

        note = self.get_object()

        if is_htmx:
            html = cache_deps.get_from_cache(htmx_cache_key)
            if not html:
                html = render_to_string(
                    "partials/note_detail.html", {"note": note}, request=request
                )
                cache_deps.set_from_cache(htmx_cache_key, html, 60 * 2)

            return HttpResponse(html)

        data = cache_deps.get_from_cache(json_cache_key)
        if not data:
            serializer = self.get_serializer(note)
            data = serializer.data
            cache_deps.set_from_cache(json_cache_key, data, 60 * 5)

        return Response(data)

    def perform_create(self, serializer):
        user = self.request.user
        tag_id = self.request.data.get("tag_id")

        if not tag_id:
            raise ValidationError({"tag_id": "This field is required"})
        tag_uuid = uuid.UUID(tag_id)

        tag = crud_actions.first(model=Tag, id=tag_uuid, user=user, is_deleted=False)

        if not tag:
            raise ValidationError({"tag_id": "Tag does not exist"})

        if crud_actions.exists(model=Note, tag=tag, user=user, is_deleted=False):
            raise ValidationError(
                {"tag_id": "This tag is already assigned to another note"}
            )

        note = serializer.save(user=user, tag=tag)

        send_note_update(
            user_id=user.id,
            data={
                "action": "create",
                "note_id": str(note.id),
                "title": note.title,
                "content": note.decrypted_content(),
                "tag": str(note.tag.id),
            },
        )

        add_to_sync_queue(note, "create")
        cache_deps.delete_many_from_cache(
            f"notes_user_json_{user.id}", f"notes_user_html_{user.id}"
        )

    def perform_update(self, serializer):
        note = self.get_object()
        user = self.request.user

        if note.user != user:
            raise PermissionDenied("You cannot edit this note")

        update_data = {"version": note.version + 1}

        if "tag_id" in self.request.data:
            tag_id = self.request.data.get("tag_id")

            if tag_id is None:
                raise ValidationError({"tag_id": "Tag cannot be null"})

            if isinstance(tag_id, str) and not tag_id.strip():
                raise ValidationError({"tag_id": "Tag cannot be empty"})

            try:
                tag_uuid = uuid.UUID(tag_id)
            except (ValueError, TypeError):
                raise ValidationError({"tag_id": "Invalid UUID format"})

            tag = crud_actions.first(model=Tag, id=tag_uuid, user=user)

            if not tag:
                raise ValidationError({"tag_id": "Tag does not exist"})

            if crud_actions.exists(
                model=Note,
                tag=tag,
                user=user,
                is_deleted=False,
                exclude={"id": note.id},
            ):
                raise ValidationError(
                    {"tag_id": "This tag is already assigned to another note"}
                )

            update_data["tag"] = tag

        with transaction.atomic():
            note = serializer.save(**update_data)

            send_note_update(
                user_id=user.id,
                data={
                    "action": "update",
                    "note_id": str(note.id),
                    "title": note.title,
                    "content": note.decrypted_content(),
                    "tag": str(note.tag.id) if note.tag else None,
                },
            )

        add_to_sync_queue(note, "update")

        cache_deps.delete_many_from_cache(
            f"note_htmx_{user.id}_{note.id}",
            f"note_json_{user.id}_{note.id}",
            f"notes_user_json_{user.id}",
            f"notes_user_html_{user.id}",
        )

    def perform_destroy(self, instance):
        user = self.request.user
        if instance.user != user:
            raise PermissionDenied("You cannot delete this note")

        instance.is_deleted = True
        instance.save()
        send_note_update(
            user_id=user.id,
            data={
                "action": "delete",
                "note_id": str(instance.id),
            },
        )
        add_to_sync_queue(instance, "delete")
        cache_deps.delete_many_from_cache(
            f"notes_user_html{self.request.user.id}",
            f"notes_user_json{self.request.user.id}",
            f"note_html_{self.request.user.id}_{instance.id}",
            f"note_json_{self.request.user.id}_{instance.id}",
        )
