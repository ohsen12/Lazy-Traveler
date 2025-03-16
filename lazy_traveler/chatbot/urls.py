from django.urls import path
from .views import ChatBotView, ChatHistoryView
app_name = "chatbot"

urlpatterns = [
    
    path("chat/", ChatBotView.as_view(), name="chatbot"),
    path("chat-history/", ChatHistoryView.as_view(), name="chat_history"),

]
