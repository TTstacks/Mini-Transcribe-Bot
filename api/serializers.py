from django.contrib.auth.models import User
from rest_framework import serializers

from api.models import TranscriptionJob


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(username=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class JobSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = TranscriptionJob
        fields = [
            "id",
            "status",
            "duration_seconds",
            "duration_minutes",
            "transcript",
            "report",
            "error_message",
            "created_at",
            "updated_at",
        ]

    def get_duration_minutes(self, obj):
        return round(obj.duration_seconds / 60, 2)

