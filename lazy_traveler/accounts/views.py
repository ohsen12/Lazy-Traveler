from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignupSerializer
from collections import defaultdict
from chatbot.models import ChatHistory
from django.contrib.auth import get_user_model


# 로그인과 함께 진행되어야 할 access, refresh 토큰 발급은 TokenObtainPairView 클래스 뷰와 연결하여 처리한다.


# user 검증 로직
class BaseUserView(APIView):
    permission_classes = [IsAuthenticated]


# 회원가입
class SignupView(APIView):
    
    permission_classes = [AllowAny]
    
    # POST 요청으로 username, password, password2, tags 가 넘어왔음
    def post(self, request):
        # 시리얼라이저 인스턴스 생성
        serializer = SignupSerializer(data=request.data)
        
        # 유효성 검사
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()  # 새 사용자 생성
            return Response(
                {
                    "message": "Sign-up completed.",
                    "id": user.id, 
                    "username":user.username,
                    "tags": user.tags
                },
                status=status.HTTP_201_CREATED
            )
                

# 아이디 중복 체크
class CheckUsernameView(APIView):
    
    permission_classes = [AllowAny]
    
    # 요청에서 username을 받았음
    def post(self, request):
        username = request.data.get("username", "")
        
        if get_user_model().objects.filter(username=username).exists():
            return Response(
                    {"message":"사용할 수 없는 ID입니다"},
                    status=status.HTTP_409_CONFLICT 
                )
        else:
            return Response(
                    {"message":"사용 가능한 ID입니다"},
                    status=status.HTTP_200_OK       
                )
            

# 로그아웃
class LogoutView(BaseUserView):
    
    def post(self, request):
        try:
            # 요청에서 보낸 'refresh_token'에 담긴 토큰을 꺼낸다.
            refresh_token = request.data.get('refresh_token')
            # 만약 요청에 담겨온 리프레시 토큰이 없다면
            if not refresh_token:
                return Response(
                    {"message": "No refresh token provided"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # refresh 토큰 객체 생성
            token = RefreshToken(refresh_token)
            # 토큰 만료 후 재사용 불가하도록 블랙리스트에 추가
            token.blacklist()
            return Response(
                {
                    "message": "Successfully logged out.",
                    "username": request.user.username
                }, status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# 마이페이지
class MyPageView(BaseUserView):
    def get(self, request):
        user = request.user
        
        return Response({
                'username':user.username,
                'tags': user.tags
            },
            status=status.HTTP_200_OK
        )


# 패스워드 수정
class UpdatePasswordView(BaseUserView):
    
    # 현재 비밀번호, 새로운 비밀번호
    def post(self, request):
        user = request.user
        
        current_password = request.data.get("current_password")
        # 입력한 현재 비밀번호가 실제 현재 비밀번호와 같은지 해싱 비교
        if not user.check_password(current_password):
            return Response(
                {'error': '현재 비밀번호가 일치하지 않습니다'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        new_password = request.data.get('new_password')
        # 현재 비밀번호와 같은지 해싱 비교
        if user.check_password(new_password):
            return Response(
                {'error': '새로운 비밀번호는 기존 비밀번호와 동일할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 비밀번호 업데이트
        try:
            user.set_password(new_password) # 평문 암호화
            user.save() # 저장
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': '비밀번호가 성공적으로 변경되었습니다.'},
                        status=status.HTTP_200_OK)


# 태그 업데이트
class UpdateTagsView(BaseUserView):
    
    def get(self, request):
        '''화면에 현재 태그 노출'''
        user = request.user
        
        current_tags = user.tags
        
        return Response({
            'tags': current_tags
        })
        
    def put(self, request):
        '''태그 업데이트'''
        user = request.user
        new_tags = request.data.get('tags')

        if new_tags is None:
            return Response({'error': 'tags는 필수 항목입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 새로운 태그를 저장
        user.tags = new_tags
        user.save(update_fields=['tags'])

        return Response({'message': '태그가 성공적으로 변경되었습니다.'}, status=status.HTTP_200_OK)


# 회원 탈퇴
class DeleteAccountView(BaseUserView):
    def delete(self, request):
        # 로그인한 사용자를 DB에서 삭제한다.
        request.user.delete()
        # 성공 메세지 반환
        return Response({"message": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT)