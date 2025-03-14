from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView
from .views import DeleteAccountView, LogoutView, SignupView, UpdatePasswordView, UpdateTagsView, UserHistoryView

app_name = "accounts"

urlpatterns = [
    
    path("signup/", SignupView.as_view(), name="signup"), # 회원가입
    path("login/", TokenObtainPairView.as_view(), name="login"), # 로그인
    path("logout/", LogoutView.as_view(), name="logout"), # 로그아웃
    path('update_password/', UpdatePasswordView.as_view(), name='update_password'), # 패스워드 수정
    path('update_tags/', UpdateTagsView.as_view(), name='update_tags'), # 태그 수정
    path('delete_account/', DeleteAccountView.as_view(), name='delete_account'), # 회원 탈퇴
    path('user_history/', UserHistoryView.as_view(), name='user_history'), # 대화 내역

    # 토큰 갱신 - 프론트에서 필요
    # path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]