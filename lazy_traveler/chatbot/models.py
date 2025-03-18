from django.db import models
from django.contrib.auth import get_user_model


class ChatHistory(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, default=1)  # 기본값을 ID=1로 설정
    message = models.TextField()  # 사용자의 메시지
    response = models.TextField()  # 챗봇의 응답
    created_at = models.DateTimeField(auto_now_add=True)  # 대화 시간
    session_id = models.CharField(max_length=255)  # 세션 ID

    def __str__(self):
        return f"{self.user} - {self.message[:20]}"