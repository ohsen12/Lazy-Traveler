from django.urls import path
from .views import RefreshConversationView,LogoutView #ScheduleMenuView

urlpatterns = [
    # 리프레시(로고 클릭)
    path('refresh-conversation/', RefreshConversationView.as_view(), name='refresh-conversation'),
    # 로그아웃 엔드포인트 추가
    path('logout/',LogoutView.as_view(), name='logout'),  
    # 스케줄러 메뉴 (GET: 스케줄 조회, 시간대별 추천 / POST: 스케줄 생성)
    # path('schedule-menu/', ScheduleMenuView.as_view(), name='schedule-menu'),
    ]