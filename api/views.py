from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from api.audio import get_audio_duration_seconds, validate_audio_extension
from api.authentication import EmailTokenObtainPairSerializer
from api.models import TranscriptionJob
from api.serializers import JobSerializer, RegisterSerializer
from api.services import process_job


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"id": user.id, "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer


class JobDetailView(RetrieveAPIView):
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TranscriptionJob.objects.filter(owner=self.request.user)


class JobCreateView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        audio = request.FILES.get("audio")
        if audio is None:
            raise ValidationError({"audio": "Audio file is required."})

        validate_audio_extension(audio.name)
        saved_path = default_storage.save(f"audio/{audio.name}", audio)
        full_path = default_storage.path(saved_path)

        try:
            duration_seconds = get_audio_duration_seconds(full_path)
            remaining_seconds = self.get_remaining_seconds(request.user)
            if duration_seconds > remaining_seconds:
                default_storage.delete(saved_path)
                return Response(
                    {
                        "detail": "Audio exceeds remaining free limit.",
                        "remaining_minutes": round(remaining_seconds / 60, 2),
                        "limit_minutes": settings.AUDIO_LIMIT_MINUTES,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            job = TranscriptionJob.objects.create(
                owner=request.user,
                audio=saved_path,
                duration_seconds=duration_seconds,
            )
            process_job(job)
        except Exception:
            if "job" not in locals() and default_storage.exists(saved_path):
                default_storage.delete(saved_path)
            raise

        return Response({"job_id": job.id}, status=status.HTTP_201_CREATED)

    def get_remaining_seconds(self, user):
        used_seconds = sum(
            user.transcription_jobs.values_list("duration_seconds", flat=True)
        )
        return max((settings.AUDIO_LIMIT_MINUTES * 60) - used_seconds, 0)


class UsageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        used_seconds = sum(
            request.user.transcription_jobs.values_list("duration_seconds", flat=True)
        )
        used_minutes = round(used_seconds / 60, 2)
        remaining_minutes = max(settings.AUDIO_LIMIT_MINUTES - used_minutes, 0)
        return Response(
            {
                "used_minutes": used_minutes,
                "remaining_minutes": round(remaining_minutes, 2),
                "limit_minutes": settings.AUDIO_LIMIT_MINUTES,
            }
        )
