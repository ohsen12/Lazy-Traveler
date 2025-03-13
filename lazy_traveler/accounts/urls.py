from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView
from .views import DeleteAccountView, LogoutView, SignupView, UpdatePasswordView, UpdateTagsView 

app_name = "accounts"

urlpatterns = [
    # 회원가입/로그인/로그아웃
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path('update_password/', UpdatePasswordView.as_view(), name='update_password'),
    path('update_tags/', UpdateTagsView.as_view(), name='update_tags'),
    path('delete_account/', DeleteAccountView.as_view(), name='delete_account'),

    # 토큰 갱신 - 프론트에서 필요
    # path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]