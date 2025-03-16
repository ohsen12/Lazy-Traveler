from django.urls import path
from .views import ChatBotView, ChatHistoryView, SessionHistoryView
app_name = "chatbot"

urlpatterns = [
    
    path("chat/", ChatBotView.as_view(), name="chatbot"),
    path("chat-history/", ChatHistoryView.as_view(), name="chat_history"),
    path("session-history/", SessionHistoryView.as_view(), name="session_history"),

]
