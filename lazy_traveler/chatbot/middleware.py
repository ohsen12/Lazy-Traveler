from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken
from accounts.models import User  # 모델 임포트 (accounts_user 모델을 가져오기)

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        token = self.get_token_from_scope(scope)

        if token is not None:
            user_id = await self.get_user_from_token(token)
            if user_id:
                # 유효한 사용자 ID를 scope에 추가
                scope["user"] = await self.get_user_from_id(user_id)  # user 객체 추가
            else:
                scope["error"] = "invalid_token"
        else:
            scope["error"] = "no_token"

        return await super().__call__(scope, receive, send)

    def get_token_from_scope(self, scope):
        query_string = parse_qs(scope.get("query_string", b"").decode("utf-8"))
        return query_string.get("token", [None])[0]

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            access_token = AccessToken(token)
            return access_token["user_id"]
        except (TokenError, InvalidToken) as e:
            print(f"토큰 검증 실패: {e}")
            return None

    @database_sync_to_async
    def get_user_from_id(self, user_id):
        try:
            return User.objects.get(id=user_id)  # user_id를 사용하여 user 객체를 가져옴
        except User.DoesNotExist:
            return None
