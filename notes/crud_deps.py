from typing import Optional, Type, TypeVar

from django.db import IntegrityError
from django.db.models import Model, QuerySet
from django.core.exceptions import ValidationError
from django.db import transaction
T = TypeVar("T", bound=Model)


class ExistingDependencies:
    async def async_check_existing(
        self, model: Type[T], raise_error_if_exists=True, error_field="Record", **kwargs
    ):
        obj = await model.objects.filter(**kwargs).aexists()
        if raise_error_if_exists and obj:
            raise ValidationError(f"{error_field} already exists.")
        if not raise_error_if_exists and not obj:
            raise ValidationError(f"{error_field} not found.")
        return obj


class CRUDDependencies:

    async def aget_object(self, model: Type[T], **filters) -> Optional[T]:
        try:
            return await model.objects.aget(**filters)
        except model.DoesNotExist:
            return None

    def get_object(self, model: Type[T], **filters) -> Optional[T]:
        try:
            return model.objects.get(**filters)
        except model.DoesNotExist:
            return None

    def create_object(self, model: Type[T], **data) -> T:
        try:
            
            return model.objects.create(**data)
        except IntegrityError:
            return None

    def get_or_create(self, model: Type[T], defaults=None, **filters) -> tuple[T, bool]:
        return model.objects.get_or_create(defaults=defaults or {}, **filters)

    def get_only(self, model: Type[T], only: list[str], **filters) -> Optional[T]:
        try:
            return model.objects.filter(**filters).only(*only)
        except model.DoesNotExist:
            return None

    def count(self, model: Type[T], **filters) -> int:
        queryset = model.objects.filter(
            **filters) if filters else model.objects.all()
        return queryset.count()

    def exists(self, model: Type[T], **filters) -> bool:
        try:
            return model.objects.filter(**filters).exists()
        except model.DoesNotExist:
            return None

    def filter(self, model: Type[T], **filters) -> Optional[T]:
        try:
            return model.objects.filter(**filters)
        except model.DoesNotExist:
            return None

    def filter_by_select_related(
        self,
        model: Type[T],
        fields,
        **filters
    ) -> QuerySet[T]:

        if isinstance(fields, str):
            fields = [fields]

        return model.objects.filter(**filters).select_related(*fields)

    def first(self, model: Type[T], **kwargs) -> Optional[T]:
        try:
            return model.objects.filter(**kwargs).first()
        except model.DoesNotExist:
            return None

    def get_list(
        self,
        model: Type[T],
        select_related: list[str] | None = None,
        prefetch_related: list[str] | None = None,
        limit: int | None = None,
        **filters,
    ) -> list[T]:
        queryset = model.objects.filter(**filters)

        if select_related:
            queryset = queryset.select_related(*select_related)

        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)

        if limit:
            queryset = queryset[:limit]

        return list(queryset)

    def get_single_related_without_filter(
        self,
        model: Type[T],
        select_related: str | None = None,
        prefetch_related: str | None = None,
    ) -> QuerySet[T]:

        queryset = model.objects.all()

        if select_related:
            if isinstance(select_related, str):
                select_related = [select_related]
            queryset = queryset.select_related(*select_related)

        if prefetch_related:
            if isinstance(prefetch_related, str):
                prefetch_related = [prefetch_related]
            queryset = queryset.prefetch_related(*prefetch_related)

        return queryset

    def update(self, model: Type[T], filters: dict, updates: dict) -> int:
        try:
            return model.objects.filter(**filters).update(**updates)
        except IntegrityError:
            return None

    def delete(self, model: Type[T], **filters) -> int:
        with transaction.atomic():
            deleted_count, _ = model.objects.filter(**filters).delete()
        return deleted_count


crud_actions = CRUDDependencies()
