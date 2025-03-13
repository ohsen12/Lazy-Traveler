from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    username = models.CharField(max_length=50, unique=True)  # username 필드 중복 방지
    password = models.CharField(max_length=128) 
    created_at = models.DateTimeField(auto_now_add=True)
    # 쉼표(,)로 구분된 문자열(ex."맛집,카페,한식") 저장. 저장된 값을 쉼표로 분리해서 리스트로 변환할 수 있음. 
    # 프론트엔드에서는 이를 "맛집,카페,한식" 이런 식으로 하나의 문자열로 서버에 전송해야 함.
    tags = models.TextField(blank=True, default="") 


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    characteristics = models.CharField(max_length=255, null=True, blank=True)
    recommendation_keywords = models.JSONField(null=True, blank=True)
    
    def __str__(self):
        return f'Profile of {self.user.username}'


# 사용자의 대화 내역을 저장하는 모델
class Conversation(models.Model):
    user = models.ForeignKey(User, related_name='conversations', on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    
# 사용자가 선택한 경로(방문 동선)을 저장하는 모델
class UserSelectedPath(models.Model):
    user = models.ForeignKey(User, related_name='selected_paths', on_delete=models.SET_NULL, null=True)
    selected_path = models.JSONField()
    created_at = models.DateField(auto_now_add=True)
    
    
# 탈퇴한 유저 정보를 저장하는 모델
# class DeletedUser(models.Model):
#     original_user_id = models.CharField(max_length=255)
#     password = models.CharField(max_length=128)
#     characteristics = models.CharField(max_length=255, null=True, blank=True)
#     recommendation_keywords = models.JSONField(null=True, blank=True)
#     deleted_at = models.DateTimeField(auto_now_add=True)
#     retention_until = models.DateTimeField(null=True, blank=True)
    
#     def __str__(self):
#         return self.original_user_id
