from django.urls import path

from api.views import JobCreateView, JobDetailView, LoginView, RegisterView, UsageView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("aut/refresh", TokenRefreshView.as_view(), name="auth-refresh"),
    path("jobs", JobCreateView.as_view(), name="job-create"),
    path("jobs/<int:pk>", JobDetailView.as_view(), name="job-detail"),
    path("me/usage", UsageView.as_view(), name="usage"),
]
