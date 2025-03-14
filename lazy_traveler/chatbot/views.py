import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import ChatHistory
from .serializers import ChatHistorySerializer
from .chat_logic import get_recommendation
from django.db.models import Min
from django.db.models import F

DEFAULT_CHAT_LIMIT = 50  # 기본 조회 개수 제한


class ChatBotView(APIView):
    
    def post(self, request):
        """
        사용자가 메시지를 입력하면 응답을 생성하고, 해당 세션에 저장합니다.
        새로운 대화 시작 시 새로운 session_id를 생성할 수 있습니다.
        """
        user = request.user if request.user.is_authenticated else None
        user_query = request.data.get("message", "")
        session_id = request.data.get("session_id", None)
        new_session = request.data.get("new_session", False)  # 새로운 대화 시작 여부

        # 세션에서 위도, 경도 가져오기
        latitude = request.session.get('latitude')
        longitude = request.session.get('longitude')
        print(f"📍 현재 위치: 위도 {latitude}, 경도 {longitude}")


        if not user_query:
            return Response({"error": "메시지를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # 새로운 세션이면 UUID 생성
        if new_session or not session_id:
            # ✅ 랜덤한 UUID(Universally Unique Identifier) 객체를 생성하여 문자열로 변환
            session_id = str(uuid.uuid4())

        # 챗봇 응답 생성 (✅ response_text에는 모델 응답의 content가 담김)
        response_text = get_recommendation(user_query, session_id, latitude, longitude)

        # 대화 내역 저장
        chat_data = {
            "username": user.username if user else "익명",
            "message": user_query,
            "response": response_text,
            "session_id": session_id
        }

        # 대화 내역을 DB에 저장
        ChatHistory.objects.create(
            username=user.username if user else "익명",
            message=user_query,
            response=response_text,
            session_id=session_id
        )

        return Response(chat_data, status=status.HTTP_200_OK)




class ChatHistoryView(APIView):
    """
    특정 유저의 대화 기록을 세션별로 조회하는 API.
    - `session_id`가 주어지면 해당 세션의 모든 대화를 반환.
    - `session_id`가 없으면, 사용자의 전체 세션 목록을 반환.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        session_id = request.query_params.get("session_id", None)

        if session_id:
            # 특정 세션 ID에 대한 대화 조회
            chats = ChatHistory.objects.filter(username=user.username, session_id=session_id).order_by("created_at")
            if not chats.exists():
                return Response({
                    "error": f"세션 ID `{session_id}`에 대한 대화 내역이 없습니다. 올바른 ID를 입력했는지 확인해주세요."
                }, status=status.HTTP_404_NOT_FOUND)
            return Response(ChatHistorySerializer(chats, many=True).data, status=status.HTTP_200_OK)

        # 전체 세션 목록 조회 (✅ annotate: 각 세션의 첫 메시지만 가져옴, order_by: 첫 메시지의 생성 시간을 기준으로 내림차순 정렬. 즉, 가장 최근에 시작된 세션이 먼저 오게 됨.)
        sessions = ChatHistory.objects.filter(username=user.username).values('session_id')\
            .annotate(first_message=Min('created_at'))\
            .order_by('-first_message')
        
        # 세션 ID, 첫 메시지, 첫 메시지 생성 시간을 포함하는 딕셔너리 목록
        session_list = [
            {
                "session_id": session['session_id'],
                "first_message": ChatHistory.objects.filter(username=user.username, session_id=session['session_id'])\
                    .order_by('created_at').first().message,
                "created_at": session['first_message']
            }
            for session in sessions
        ]
        return Response(session_list, status=status.HTTP_200_OK)



@api_view(['POST'])
def save_location(request):
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')

    if latitude and longitude:
        # 📍 세션에 위치 정보 저장
        request.session['latitude'] = latitude
        request.session['longitude'] = longitude
        request.session.modified = False  # 세션 갱신
        print(f"📍 저장된 위치: 위도 {latitude}, 경도 {longitude}")
        return Response({"message": "위치 저장 완료!", "latitude": latitude, "longitude": longitude}, status=status.HTTP_200_OK)
    else:
        return Response({"error": "위치 데이터 없음"}, status=status.HTTP_400_BAD_REQUEST)