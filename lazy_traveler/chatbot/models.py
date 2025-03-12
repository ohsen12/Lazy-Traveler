from django.db import models


class ChatHistory(models.Model):
    username = models.CharField(max_length=255)  # 사용자 이름
    message = models.TextField()  # 사용자의 메시지
    response = models.TextField()  # 챗봇의 응답
    created_at = models.DateTimeField(auto_now_add=True)  # 대화 시간
    session_id = models.CharField(max_length=255)  # 세션 ID

    def __str__(self):
        return f"{self.username} - {self.message[:20]}"