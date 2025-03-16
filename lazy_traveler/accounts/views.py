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
                    "detail": "Sign-up completed.",
                    "id": user.id, 
                    "username":user.username,
                    "tags": user.tags
                },
                status=status.HTTP_201_CREATED
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
                    {"detail": "No refresh token provided"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # refresh 토큰 객체 생성
            token = RefreshToken(refresh_token)
            # 토큰 만료 후 재사용 불가하도록 블랙리스트에 추가
            token.blacklist()
            return Response(
                {
                    "detail": "Successfully logged out.",
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
    def post(self, request):
        user = request.user
        
        new_password = request.data.get('new_password')
        if not new_password:
            return Response({
                'error': 'new_password는 필수 항목입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
        user = request.user
        
        current_tags = user.tags
        
        return Response({
            'tags': current_tags
        })
        
    def put(self, request):
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
        
        
# 대화내역 조회
class UserHistoryView(BaseUserView):
    def get(self, request):
        # 해당 user를 가져옴
        user = request.user
        
        # 해당 user의 모든 대화 인스턴스를 DB에서 내림차순으로 가져옴
        histories = ChatHistory.objects.filter(user=user).order_by('-created_at')
        
        # grouped_data: 특정 날짜를 키로 하는 대화 목록
        # defaultdict(list): 새로운 키에 자동으로 빈 리스트를 할당)
        grouped_data = defaultdict(list)
        
        # 각 날짜별로 그룹화
        for history in histories:
            # YYYY-MM-DD 형식으로 변환 (date():datetime 객체에서 시간 제외하고 날짜(YYYY-MM-DD)만 반환/ isoformat(): date 객체를 문자열로 반환)
            date_key = history.created_at.date().isoformat()  
            # 각 날짜 키에 대화 딕셔너리 추가 (디폴트 값인 빈리스트에 차례로 추가됨)
            grouped_data[date_key].append({
                
                "message": history.message,
                "response": history.response,
                "created_at": history.created_at.isoformat() 
                
            })

        # 최신 날짜별 정렬 
        # grouped_data.items(): 딕셔너리의 모든 키(날짜)-값(대화내역)쌍을 튜플로 반환한 것
        sorted_data = {
            date: sorted(messages, key=lambda x: x["created_at"], reverse=True)  # ✅ 각 날짜 안의 대화내역은 최신순 정렬(각 객체의 created_at 기준)
            for date, messages in sorted(grouped_data.items(), key=lambda x: x[0], reverse=True) # date(키) 기준 최신순 정렬 (message: 대화 딕셔너리를 담고 있는 리스트)
        }

        return Response(sorted_data)
