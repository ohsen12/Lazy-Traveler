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
from .models import User, Profile, Conversation, UserSelectedPath, DeletedUser

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
# 사용자의 특성(characteristics)과 추천 키워드(recommendation_keywords)를 업데이트
class UpdateTagsView(BaseUserView):
    def post(self, request):
        user, error_response = self.get_validated_user(request, from_query_params=False)
        if error_response:
            return error_response
        
        characteristics = request.data.get('characteristics')
        recommendation_keywords = request.data.get('recommendation_keywords')
        
        profile, created = Profile.objects.get_or_create(user=user)
        
        if characteristics:
            profile.characteristics = characteristics
        if recommendation_keywords:
            profile.recommendation_keywords = recommendation_keywords
        
        try:
            profile.save()
        except DatabaseError:
            return Response({'error': '태그 정보 업데이트 중 오류가 발생했습니다.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'message': '태그 정보가 성공적으로 업데이트 되었습니다.'},
                        status=status.HTTP_200_OK)


# ------------------------------------------------------------------------------
# SaveConversationView
# ------------------------------------------------------------------------------
# 사용자의 대화 내역을 저장
class SaveConversationView(BaseUserView):
    def post(self, request):
        user, error_response = self.get_validated_user(request, from_query_params=False)
        if error_response:
            return error_response
        
        content = request.data.get('content')
        if not content:
            return Response({'error': 'content는 필수 항목입니다.'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        try:
            Conversation.objects.create(user=user, content=content)
        except DatabaseError:
            return Response({'error': '대화 내역 저장 중 오류가 발생했습니다.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'message': '대화 내역이 저장되었습니다.'},
                        status=status.HTTP_200_OK)

# ------------------------------------------------------------------------------
# ConversationSummaryView
# ------------------------------------------------------------------------------
# 최근 7일간의 대화 내역을 일별로 집계하고, 사용자가 선택한 경로의 최신 데이터를 반환
class ConversationSummaryView(BaseUserView):
    def get(self, request):
        user, error_response = self.get_validated_user(request, from_query_params=True)
        if error_response:
            return error_response
        
        try:
            start_date = timezone.now() - timedelta(days=7)
            conversations = Conversation.objects.filter(user=user, created_at__gte=start_date)
            summary = {}
            for conv in conversations:
                date_str = conv.created_at.strftime('%Y-%m-%d')
                summary[date_str] = summary.get(date_str, 0) + 1
            
            # UserSelectedPath를 사용하여 사용자가 선택한 경로 중 최신 데이터를 조회
            final_path_obj = UserSelectedPath.objects.filter(user=user).order_by('-created_at').first()
            final_path_data = final_path_obj.visited_path if final_path_obj else None
        except DatabaseError:
            return Response({'error': '대화 요약 조회 중 오류가 발생했습니다.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            '일별_대화_요약': summary,
            '최종_방문_동선': final_path_data
        }, status=status.HTTP_200_OK)

# ------------------------------------------------------------------------------
# SaveFinalVisitedPathView
# ------------------------------------------------------------------------------
# 사용자가 선택한 경로(방문 동선)을 저장
class SaveFinalVisitedPathView(BaseUserView):
    def post(self, request):
        user, error_response = self.get_validated_user(request, from_query_params=False)
        if error_response:
            return error_response
        
        visited_path = request.data.get('visited_path')
        if not visited_path:
            return Response({'error': 'visited_path는 필수 항목입니다.'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        try:
            UserSelectedPath.objects.create(user=user, visited_path=visited_path)
        except DatabaseError:
            return Response({'error': '방문 동선 저장 중 오류가 발생했습니다.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'message': '최종 방문 동선이 저장되었습니다.'},
                        status=status.HTTP_200_OK)

# ------------------------------------------------------------------------------
# RecommendationsView
# ------------------------------------------------------------------------------
# 추천 장소(더미 데이터)를 반환
class RecommendationsView(BaseUserView):
    def get(self, request):
        user, error_response = self.get_validated_user(request, from_query_params=True)
        if error_response:
            return error_response
        
        dummy_recommendations = [
            {'place_id': 'p1', 'name': '추천 장소 1', 'description': '설명 1'},
            {'place_id': 'p2', 'name': '추천 장소 2', 'description': '설명 2'},
            {'place_id': 'p3', 'name': '추천 장소 3', 'description': '설명 3'}
        ]
        return Response({'추천_장소': dummy_recommendations},
                        status=status.HTTP_200_OK)

# ------------------------------------------------------------------------------
# DeleteAccountView
# ------------------------------------------------------------------------------
# 회원 탈퇴 시, 탈퇴 정보를 DeletedUser 테이블에 보관하고, User 테이블에서는 삭제
# 보관 정보의 만료일은 현재 시각으로부터 1년 후로 설정하며, 트랜잭션 블록을 사용하여 원자적(atomic)으로 처리
class DeleteAccountView(BaseUserView):
    def post(self, request):
        user, error_response = self.get_validated_user(request, from_query_params=False)
        if error_response:
            return error_response
        
        try:
            with transaction.atomic():
                retention_until = timezone.now() + timedelta(days=365)
                DeletedUser.objects.create(
                    original_user_id=user.id,
                    password=user.password,
                    characteristics=user.profile.characteristics,
                    recommendation_keywords=user.profile.recommendation_keywords,
                    deleted_at=timezone.now(),
                    retention_until=retention_until
                )
                user.delete()
        except DatabaseError:
            return Response({'error': '회원 탈퇴 처리 중 오류가 발생했습니다.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'message': '회원 탈퇴가 완료되었습니다.'},
                        status=status.HTTP_200_OK)