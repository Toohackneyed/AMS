from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

# Custom authentication backend that allows login with email
class EmailBackEnd(ModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        print(f"Authenticating user with email: {username}")
        UserModel = get_user_model()
        user = UserModel.objects.filter(email=username).first()
        if user is None:
            return None
        if user.check_password(password):
            return user
        return None
