from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    username = models.CharField(max_length=50, unique=True)  # username 필드 중복 방지
    password = models.CharField(max_length=128) 
    created_at = models.DateTimeField(auto_now_add=True) 
