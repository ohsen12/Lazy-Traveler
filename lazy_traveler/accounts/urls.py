from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView
from .views import LogoutView, SignupView

app_name = "accounts"

urlpatterns = [
    # 회원가입/로그인/로그아웃
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # 토큰 갱신 - 프론트에서 필요
    # path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]