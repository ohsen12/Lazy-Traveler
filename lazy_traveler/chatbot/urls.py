from django.urls import path
from .views import ChatBotView, ChatHistoryView
from chatbot import views
app_name = "chatbot"

urlpatterns = [
    path("chat/", ChatBotView.as_view(), name="chatbot"),
    path("chat-history/", ChatHistoryView.as_view(), name="chat_history"),
    path("save-location/", views.save_location, name='save-location'),  # 위치 저장 API 추가

]
