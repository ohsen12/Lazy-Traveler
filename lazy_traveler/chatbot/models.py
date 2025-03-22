from django.db import models
from django.conf import settings  # settings에서 사용자 모델 참조


class ChatHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=1)  # 문자열 참조 방식
    message = models.TextField()  # 사용자의 메시지
    response = models.TextField()  # 챗봇의 응답
    created_at = models.DateTimeField(auto_now_add=True)  # 대화 시간
    session_id = models.CharField(max_length=255)  # 세션 ID

    def __str__(self):
        return f"{self.user} - {self.message[:20]}"