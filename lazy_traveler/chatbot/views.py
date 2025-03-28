import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import ChatHistory
from .serializers import ChatHistorySerializer
from .recommendation_service import get_recommendation
from .place_constructor import extract_place_info, process_place_info
# ----
from accounts.models import User, Place
from django.db.models import Min
from collections import defaultdict
from .recommendations import process_recommendations, extract_places_from_response
import json
import logging

logger = logging.getLogger(__name__)



class ChatBotView(APIView):
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        로그인한 사용자만 session_id를 부여받고, 대화 내역을 DB에 저장합니다.
        로그인하지 않은 사용자는 session_id 없이 응답만 받습니다.
        """
        user = request.user if request.user.is_authenticated else None
        username = user.username if user else "Guest"  # 로그인하지 않은 경우에는 'Guest'로 설정
        user_query = request.data.get("message", "").strip()
        new_session = request.data.get("new_session", False)  # ✅ 새로운 대화 시작 여부 (추후 프론트에서 수정)

        # 세션에서 위도, 경도 가져오기
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        print(f"📍 현재 위치: 위도 {latitude}, 경도 {longitude}")

        if not user_query:
            return Response({"error": "메시지를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # 로그인한 경우에만 session_id 부여
        session_id = request.data.get("session_id", None)
        if user and (new_session or not session_id):
            session_id = str(uuid.uuid4())  # 로그인한 경우에는 새로운 session_id 생성

        try:
            # 챗봇 응답 생성
            response_text = get_recommendation(user_query, session_id, username, latitude, longitude)
            
            # 로깅 추가
            logger.info(f"Chatbot response: {response_text[:100]}...")
            
            # 추천 알고리즘 처리
            try:
                # HTML 응답에서 장소 추출
                recommended_places = extract_places_from_response(response_text)
                logger.info(f"Extracted places: {recommended_places}")
                
                # 추출된 장소가 있으면 추가 처리
                if recommended_places:
                    processed_recommendations = process_recommendations(recommended_places)
                    logger.info(f"Processed recommendations: {processed_recommendations}")
                    
                    # 응답 데이터에 추천 정보 추가
                    response_data = {
                        "message": user_query,
                        "response": response_text,
                        "recommendations": processed_recommendations,
                        "session_id": session_id
                    }
            except Exception as e:
                logger.error(f"Error processing recommendations: {str(e)}")
                # 추천 처리 실패해도 기본 응답은 반환
            
            # 로그인한 사용자만 대화 내역 저장
            if user:
                ChatHistory.objects.create(
                    user=user,
                    message=user_query,
                    response=response_text,
                    session_id=session_id
                )
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in ChatbotView: {str(e)}")
            return Response({'error': str(e)}, status=500)


class ChatHistoryView(APIView):
    """
    특정 유저의 대화 기록을 세션 별로 조회하는 API.
    - `session_id`가 주어지면 해당 세션의 모든 대화를 반환.
    - `session_id`가 없으면, 사용자의 전체 세션 목록을 반환.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # GET 요청이므로 query_params 사용
        session_id = request.query_params.get("session_id", None)
        
        # 특정 세션 ID에 대한 대화 조회 (대화창에 표시됨)
        if session_id:
            session_history = ChatHistory.objects.filter(user=user, session_id=session_id).order_by("created_at")
            if not session_history.exists():
                return Response(
                    {
                        "error": f"세션 ID `{session_id}`에 대한 대화 내역이 없습니다. 올바른 ID를 입력했는지 확인해주세요."
                    }, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # instance를 전달하여 모델 인스턴스를 JSON 응답으로 변환 (직렬화:instance/ 역직렬화:data)
            serializer = ChatHistorySerializer(instance=session_history, many=True) 
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # 날짜 별 세션 (사이드바에 표시됨)
        else:
            # .values: session_id 필드만 포함하는 딕셔너리 리스트(QuerySet) 형태로 반환됨
            # .annotate(group by): 각 세션에 대해 created_at 필드의 최솟값을 계산하여 first_message라는 새로운 필드로 추가하는 역할
            # order_by: first_message 의 생성 시간을 기준으로 내림차순 정렬. 즉, 가장 최근에 시작된 세션이 먼저 오게 됨.
            sessions = ChatHistory.objects.filter(user=user).values('session_id')\
                .annotate(first_message=Min('created_at'))\
                .order_by('-first_message')

            # 날짜별로 세션을 그룹화하고, 첫 번째 메시지만 뽑아내는 grouped_sessions 생성 (defaultdict(list): 새로운 키에 자동으로 빈 리스트를 할당)
            grouped_sessions = defaultdict(list)

            for session in sessions:
                # 해당 session_id에 대한 첫 번째 메시지 객체
                first_message = ChatHistory.objects.filter(user=user, session_id=session['session_id']).order_by('created_at').first()

                if first_message:
                    # 첫 메시지의 날짜를 'YYYY-MM-DD' 형식으로 포맷팅
                    date_str = first_message.created_at.strftime('%Y-%m-%d')
                    
                    # 날짜별로 세션 정보 저장 (각 세션의 첫 번째 메시지)
                    grouped_sessions[date_str].append({
                        "session_id": session['session_id'],
                        "first_message": first_message.message,
                        "created_at": session['first_message'].strftime("%Y-%m-%d %H:%M") # 초 단위는 날리기
                    })
            
            # grouped_sessions는 날짜별로 세션이 그룹화된 딕셔너리를 요소로 가지는 리스트!
            session_list = [
                {
                    "date": date,  # 날짜
                    "sessions": sessions  # 해당 날짜에 속하는 세션들
                }
                for date, sessions in grouped_sessions.items()
            ]
    
            return Response(session_list, status=status.HTTP_200_OK)