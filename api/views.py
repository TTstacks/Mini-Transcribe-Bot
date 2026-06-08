from django.conf import settings
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from api.authentication import EmailTokenObtainPairSerializer
from api.models import TranscriptionJob
from api.serializers import JobSerializer, RegisterSerializer


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

