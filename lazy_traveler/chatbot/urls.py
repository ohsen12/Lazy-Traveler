from django.urls import path
from .views import ChatHistoryView
app_name = "chatbot"

urlpatterns = [
    path("chat_history/", ChatHistoryView.as_view(), name="chat_history"),
]
