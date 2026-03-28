from rest_framework import serializers
from ..models import Note, Tag
from ..crud_deps import crud_actions

class TagSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = Tag
        fields = "__all__"
       


class NoteSerializer(serializers.ModelSerializer):

    tag = TagSerializer(read_only=True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    tag_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Note
        fields = "__all__"
        read_only_fields = ("user", "version", "created_at", "updated_at")
    def validate_tag_id(self, value):
        user = self.context["request"].user
        if not crud_actions.exists(model=Tag, user=user,id=value, is_deleted=False):
            raise serializers.ValidationError("Tag does not Exist")
        return value
    def to_representation(self, instance):
        data = super().to_representation(instance)
        try:
            data["content"] = instance.decrypted_content()
        except Exception:
            data["content"] = instance.content  

        return data