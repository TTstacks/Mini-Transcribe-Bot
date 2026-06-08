from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        authenticate_kwargs = {
            "username": attrs["email"],
            "password": attrs["password"],
        }
        self.user = authenticate(**authenticate_kwargs)

        if self.user is None:
            raise self.fail("no_active_account")

        refresh = self.get_token(self.user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

