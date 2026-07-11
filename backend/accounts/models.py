from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model for ModelDoctor.
    Extending AbstractUser is a best practice to allow easy modifications
    to the User model (like adding fields or changing auth methods)
    without running into complex database migration issues later.
    """
    pass
