from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import SignupSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken


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
                    "tags": user.tags
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