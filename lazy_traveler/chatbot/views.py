import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import ChatHistory
from .serializers import ChatHistorySerializer
from .chat_logic import get_recommendation
from django.db.models import Min


DEFAULT_CHAT_LIMIT = 50  # 기본 조회 개수 제한


class ChatBotView(APIView):
    def post(self, request):
        """
        로그인한 사용자만 session_id를 부여받고, 대화 내역을 DB에 저장합니다.
        로그인하지 않은 사용자는 session_id 없이 응답만 받습니다.
        """
        user = request.user if request.user.is_authenticated else None
        username = user.username if user else "Guest"  # 로그인하지 않은 경우에는 'Guest'로 설정
        user_query = request.data.get("message", "").strip()
        new_session = request.data.get("new_session", False)  # 새로운 대화 시작 여부

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

        # 챗봇 응답 생성
        response_text = get_recommendation(user_query, session_id, username, latitude, longitude)

        # 로그인한 사용자만 대화 내역 저장
        if user:
            ChatHistory.objects.create(
                user=user,
                message=user_query,
                response=response_text,
                session_id=session_id
            )

        # 로그인 여부에 따라 응답 반환
        response_data = {
            "message": user_query,
            "response": response_text,
            
        }
        if user:
            response_data["session_id"] = session_id  # 로그인한 경우에만 session_id 포함

        return Response(response_data, status=status.HTTP_200_OK)


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

        if session_id:
            # 특정 세션 ID에 대한 대화 조회
            chats = ChatHistory.objects.filter(user=user, session_id=session_id).order_by("created_at")
            if not chats.exists():
                return Response({
                    "error": f"세션 ID `{session_id}`에 대한 대화 내역이 없습니다. 올바른 ID를 입력했는지 확인해주세요."
                }, status=status.HTTP_404_NOT_FOUND)
            return Response(ChatHistorySerializer(chats, many=True).data, status=status.HTTP_200_OK)

        # 전체 세션 목록 조회 (✅ annotate: 각 세션의 첫 메시지만 가져옴, order_by: 첫 메시지의 생성 시간을 기준으로 내림차순 정렬. 즉, 가장 최근에 시작된 세션이 먼저 오게 됨.)
        sessions = ChatHistory.objects.filter(user=user).values('session_id')\
            .annotate(first_message=Min('created_at'))\
            .order_by('-first_message')
        
        # 세션 ID, 첫 메시지, 첫 메시지 생성 시간을 포함하는 딕셔너리 목록
        session_list = [
            {
                "session_id": session['session_id'],
                "first_message": ChatHistory.objects.filter(user=user, session_id=session['session_id'])\
                    .order_by('created_at').first().message,
                "created_at": session['first_message']
            }
            for session in sessions
        ]
        return Response(session_list, status=status.HTTP_200_OK)
    

class SessionHistoryView(APIView):
    """
    각 세션 별 대화 내역을 조회하는 API
    - `session_id`를 받아 DB에서 해당 session_id를 가진 대화 객체를 모두 불러온다.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # GET 요청이므로 query_params 사용
        session_id = request.query_params.get("session_id")  

        if not session_id:
            return Response({"error": "session_id를 입력하세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 해당 session_id를 가지고 있는 인스턴스 모두 가져오기
        session_history = ChatHistory.objects.filter(session_id=session_id).order_by("created_at")
        
        # instance를 전달하여 모델 인스턴스를 JSON 응답으로 변환 (직렬화:instance/ 역직렬화:data)
        serializer = ChatHistorySerializer(instance=session_history, many=True) 
        
        return Response(serializer.data, status=status.HTTP_200_OK)
