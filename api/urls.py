from django.urls import path

from api.views import JobDetailView, LoginView, RegisterView, UsageView

urlpatterns = [
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("jobs/<int:pk>", JobDetailView.as_view(), name="job-detail"),
    path("me/usage", UsageView.as_view(), name="usage"),
]

