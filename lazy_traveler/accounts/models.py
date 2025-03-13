from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    username = models.CharField(max_length=50, unique=True)  # username 필드 중복 방지
    password = models.CharField(max_length=128) 
    created_at = models.DateTimeField(auto_now_add=True)
    # 쉼표(,)로 구분된 문자열(ex."맛집,카페,한식") 저장. 저장된 값을 쉼표로 분리해서 리스트로 변환할 수 있음. 
    # 프론트엔드에서는 이를 "맛집,카페,한식" 이런 식으로 하나의 문자열로 서버에 전송해야 함.
    tags = models.TextField(blank=True, default="") 
