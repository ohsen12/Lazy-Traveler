import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatHistory
from .recommendation_service import get_recommendation


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """클라이언트가 WebSocket에 연결될 때 실행"""
        await self.accept()

        # ✅ 사용자 정보 가져오기
        self.user = self.scope.get("user", None)  # JWT 미들웨어에서 추가한 user 객체를 가져옴
        if self.user:
            self.username = self.user.username
            self.user_info = self.user  # 비동기적으로 사용자 정보를 가져옴
            print(f"🟢 인증된 사용자: {self.username}")
        else:
            self.username = "Guest"
            self.user_info = None
            print("🟢 비로그인 사용자: Guest")

        # 새로운 session_id 생성
        self.session_id = str(uuid.uuid4())
        print(f"🟢 연결됨: {self.username} (ID: {self.user.id if self.user else 'Anonymous'})")

        await self.send(text_data=json.dumps({
            "message": f"Connected as {self.username}. Send a message to start chatting."
        }))


    async def receive(self, text_data):
        """클라이언트가 메시지를 보낼 때 실행"""
        try:
            data = json.loads(text_data)
            user_query = data.get("message", "").strip()
            new_session = data.get("new_session", False)
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            session_id = data.get("session_id")

            if not user_query:
                await self.send(text_data=json.dumps({"error": "메시지를 입력해주세요."}))
                return

            # ✅ 세션 ID 처리
            if self.user and self.user.is_authenticated:
                if new_session or not session_id:
                    self.session_id = str(uuid.uuid4())  # 새로운 세션 생성
                else:
                    self.session_id = session_id
            else:
                self.session_id = session_id or str(uuid.uuid4())  # 비로그인 사용자는 임시 세션 할당

            # ✅ 챗봇 응답 생성
            response_text = await get_recommendation(
                user_query=user_query, 
                session_id=self.session_id, 
                username=self.username, 
                latitude=latitude, 
                longitude=longitude
            )

            # ✅ 채팅 기록 저장 (로그인한 사용자만)
            if self.user and self.user.is_authenticated:
                print(f"📌 [DEBUG] save_chat_history 호출됨: {user_query}")  # 🔥 디버깅용 로그
                await self.save_chat_history(user_query, response_text)
                print(f"✅ [DEBUG] 채팅 기록 저장 완료: {user_query}")  # 🔥 저장 성공 여부 확인

            # ✅ 응답 전송
            await self.send(text_data=json.dumps({
                "message": user_query,
                "response": response_text,
                "session_id": self.session_id
            }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "잘못된 JSON 형식입니다."}))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": f"서버 오류 발생: {str(e)}"}))

    async def save_chat_history(self, user_query, response_text):
        """로그인한 사용자의 대화 내역을 비동기적으로 저장"""
        try:
            if self.user and self.user.is_authenticated:
                print(f"📌 [DEBUG] 데이터 저장 시작: {user_query}")  # 🔥 로그 추가
                await database_sync_to_async(ChatHistory.objects.create)(
                    user=self.user,
                    message=user_query,
                    response=response_text,
                    session_id=self.session_id
                )
                print(f"✅ [DEBUG] 데이터 저장 완료: {user_query}")  # 🔥 로그 추가
        except Exception as e:
            print(f"🚨 [ERROR] 채팅 기록 저장 중 오류 발생: {str(e)}")  # 🔥 오류 확인
