from datetime import timedelta
from django.db import transaction, DatabaseError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignupSerializer
from .models import User

# 로그인과 함께 진행되어야 할 access, refresh 토큰 발급은 TokenObtainPairView 클래스 뷰와 연결하여 처리한다.


#회원가입
class SignupView(APIView):
    
    permission_classes = [AllowAny]
    
    # POST 요청으로 username, password, password2 가 넘어왔음
    def post(self, request):
        # 시리얼라이저 인스턴스 생성
        serializer = SignupSerializer(data=request.data)
        
        # 유효성 검사
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()  # 새 사용자 생성
            return Response(
                {
                    "detail": "Sign-up completed.",
                    "id": user.id, 
                    "username":user.username,
                    "tags": user.tags.split(",")  # 쉼표로 구분된 문자열을 리스트로 변환하여 반환
                },
                status=status.HTTP_201_CREATED,
            )
        
        
#로그아웃
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # 요청에서 보낸 'refresh_token'에 담긴 토큰을 꺼낸다.
            refresh_token = request.data.get('refresh_token')
            # 만약 요청에 담겨온 리프레시 토큰이 없다면
            if not refresh_token:
                return Response({"detail": "No refresh token provided"}, status=400)
            
            # refresh 토큰 객체 생성
            token = RefreshToken(refresh_token)
            # 토큰 만료 후 재사용 불가하도록 블랙리스트에 추가
            token.blacklist()
            return Response(
                {
                    "detail": "Successfully logged out.",
                    "username": request.user.username
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        
# ------------------------------------------------------------------------------
# UserValidationMixin
# ------------------------------------------------------------------------------
# 클라이언트로부터 전달된 user_id를 request.data(또는 query_params)에서
# 추출하고, 필수 항목 여부 및 인증된 사용자의 ID와 일치하는지 확인한 후,
# 해당 User 객체를 반환
class UserValidationMixin:
    def get_validated_user(self, request, from_query_params=False):
        # POST 요청은 request.data, GET 요청은 query_params에서 user_id를 추출
        user_id = (request.query_params.get('user_id')
                   if from_query_params else request.data.get('user_id'))
        
        if not user_id:
            return None, Response({'error': 'user_id는 필수 항목입니다.'},
                                  status=status.HTTP_400_BAD_REQUEST)
        
        # 인증된 사용자와 요청한 user_id가 일치하는지 확인 (본인만 조작 가능)
        if str(request.user.id) != str(user_id):
            return None, Response({'error': '권한이 없습니다.'},
                                  status=status.HTTP_403_FORBIDDEN)
        
        # user_id에 해당하는 User 객체를 가져옴 (없으면 404 에러)
        user = get_object_or_404(User, pk=user_id)
        return user, None

# ------------------------------------------------------------------------------
# BaseUserView
# ------------------------------------------------------------------------------
# 이 base view는 모든 뷰에서 공통적으로 사용할 인증 및 권한 설정과 user 검증 로직을 포함하고있음
class BaseUserView(UserValidationMixin, APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

# ------------------------------------------------------------------------------
# UpdatePasswordView
# ------------------------------------------------------------------------------
# 사용자가 자신의 비밀번호를 변경할 때 사용
class UpdatePasswordView(BaseUserView):
    def post(self, request):
        # user 검증 (POST 요청에서 user_id 추출)
        user, error_response = self.get_validated_user(request, from_query_params=False)
        if error_response:
            return error_response
        
        new_password = request.data.get('new_password')
        if not new_password:
            return Response({'error': 'new_password는 필수 항목입니다.'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        # 현재 비밀번호와 같은지 해싱 비교
        if user.check_password(new_password):
            return Response({'error': '새로운 비밀번호는 기존 비밀번호와 동일할 수 없습니다.'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        # 비밀번호 업데이트 (내부에서 해싱 후 저장)
        try:
            user.set_password(new_password)
            user.save()
            print("Updated password hash:", user.password)
        except DatabaseError:
            return Response({'error': '비밀번호 업데이트 중 오류가 발생했습니다.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'message': '비밀번호가 성공적으로 변경되었습니다.'},
                        status=status.HTTP_200_OK)

# ------------------------------------------------------------------------------
# UpdateTagsView
# ------------------------------------------------------------------------------
class UpdateTagsView(BaseUserView):
    def post(self, request):
        user, error_response = self.get_validated_user(request, from_query_params=False)
        if error_response:
            return error_response
        
        try:
            user.save()
        except DatabaseError:
            return Response({'error': '태그 정보 업데이트 중 오류가 발생했습니다.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'message': '태그 정보가 성공적으로 업데이트 되었습니다.'},
                        status=status.HTTP_200_OK)


# ------------------------------------------------------------------------------
# DeleteAccountView
# ------------------------------------------------------------------------------
class DeleteAccountView(BaseUserView):
    def post(self, request):
        user, error_response = self.get_validated_user(request, from_query_params=False)
        if error_response:
            return error_response
        
        try:
            with transaction.atomic():
                # 탈퇴 정보를 DeletedUser 테이블에 기록하는 대신,
                # is_active를 False로 업데이트하여 계정을 비활성화
                user.is_active = False
                user.save(update_fields=['is_active'])
        except DatabaseError:
            return Response({'error': '회원 탈퇴 처리 중 오류가 발생했습니다.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'message': '회원 탈퇴가 완료되었습니다.'},
                        status=status.HTTP_200_OK)