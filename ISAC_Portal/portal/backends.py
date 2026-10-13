from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

class FlexibleAuthBackend(ModelBackend):
    """
    Authentication backend that supports both 'Password12345' and 'Password12345!'
    for demo accounts to avoid frustration with the exclamation mark.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # Try exact password first
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user:
            return user

        # Try variations with or without exclamation mark
        variations = []
        if password.endswith('!'):
            variations.append(password[:-1])
        else:
            variations.append(password + '!')

        for var in variations:
            user = super().authenticate(request, username=username, password=var, **kwargs)
            if user:
                return user

        return None
