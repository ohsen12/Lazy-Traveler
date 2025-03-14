from django.db import models
from accounts.models import User  # User 모델 import

class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # User 모델과 연동
    message = models.TextField()  # 사용자의 메시지
    response = models.TextField()  # 챗봇의 응답
    created_at = models.DateTimeField(auto_now_add=True)  # 대화 시간
    session_id = models.CharField(max_length=255)  # 세션 ID

    def __str__(self):
        return f"{self.user.username} - {self.message[:20]}"