from datetime import datetime
import json
import uuid
import pytz 
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatHistory
from .recommendation_LangGraph import get_recommendation
from .utils import calculate_similarity
from django.contrib.auth import get_user_model
from .recommendations import get_chat_based_recommendations, get_user_tags_by_id
from .utils import calculate_similarity

User = get_user_model()


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
            print("data:", data)
            user_query = data.get("message", "").strip()
            new_session = data.get("new_session", False)
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            session_id = data.get("session_id")
            raw_timestamp = data.get("timestamp")
            print("raw_timestamp:", raw_timestamp)


            timestamp = None
            if raw_timestamp:
                try:
                    timestamp = datetime.fromisoformat(raw_timestamp)
                    print("timestamp:", timestamp)
                except ValueError:
                    await self.send(text_data=json.dumps({"error": "올바른 timestamp 형식이 아닙니다."}))
                    return


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
                longitude=longitude,
                timestamp= timestamp ## timestamp 추가
            )
            print("response_text:", response_text)

            # ✅ 채팅 기록 저장 (로그인한 사용자만)
            if self.user and self.user.is_authenticated:
                print(f"📌 [DEBUG] save_chat_history 호출됨: {user_query}")  # 🔥 디버깅용 로그
                await self.save_chat_history(user_query, response_text.get("response"))
                print(f"✅ [DEBUG] 채팅 기록 저장 완료: {user_query}")  # 🔥 저장 성공 여부 확인

            # ✅ 응답 전송
            # await self.send(text_data=json.dumps({
            #     "message": user_query,
            #     "response": response_text,
            #     "session_id": self.session_id
            # }, ensure_ascii=False))
            
            # 추천 알고리즘 영역 추가
                recommendations = await self.get_similar_user_recommendations(self.user.id)
                print("recommendation:", recommendations)
            else:
                recommendations = None

            # await self.send(text_data=json.dumps({
            #     "message": response_text.get("user_query", user_query),
            #     "response": response_text.get("response", "응답 없음"),
            #     "session_id": self.session_id,
            #     "question_type": response_text.get("question_type", "unknown"),
            #     "question_type": recommendations
            # }, ensure_ascii=False))
            
            response_payload = {
                "message": response_text.get("user_query", user_query),
                "response": response_text.get("response", "응답 없음"),
                "session_id": self.session_id,
                "question_type": response_text.get("question_type", "unknown")
            }

            # ✅ 추천 결과가 있을 경우에만 추가
            if recommendations:
                response_payload["recommendations"] = recommendations

            # ✅ 응답 전송
            await self.send(text_data=json.dumps(response_payload, ensure_ascii=False))
            

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "잘못된 JSON 형식입니다."}))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": f"서버 오류 발생: {str(e)}"}))

    async def save_chat_history(self, user_query, response_text):
        """로그인한 사용자의 대화 내역을 비동기적으로 저장"""
        try:
            if self.user and self.user.is_authenticated:
                print(f"📌 [DEBUG] 데이터 저장 시작: {user_query}")  # 🔥 로그 추가
                if isinstance(response_text, dict):
                    response_to_save = json.dumps(response_text, ensure_ascii=False)
                else:
                    response_to_save = str(response_text)
                await database_sync_to_async(ChatHistory.objects.create)(
                    user=self.user,
                    message=user_query,
                    response=response_to_save,
                    session_id=self.session_id
                )
                print(f"✅ [DEBUG] 데이터 저장 완료: {user_query}")  # 🔥 로그 추가
        except Exception as e:
            print(f"🚨 [ERROR] 채팅 기록 저장 중 오류 발생: {str(e)}")  # 🔥 오류 확인
    
    async def get_similar_user_recommendations(self, user_id: int, top_n: int = 5):
        """
        비슷한 취향의 다른 유저들이 좋아하는 장소를 추천하는 비동기 함수
        :param user_id: 추천할 사용자 ID
        :param top_n: 최대 추천 장소 수
        :return: 추천된 장소들의 리스트
        """
        try:
            # 현재 사용자 태그
            user_tags = await get_user_tags_by_id(user_id)

            # 유사 사용자 후보
            similar_users = await database_sync_to_async(list)(User.objects.exclude(id=user_id))

            similar_user_ids = []
            for other_user in similar_users:
                other_tags = await get_user_tags_by_id(other_user.id)
                similarity = calculate_similarity(user_tags, other_tags)
                if similarity >= 0.5:
                    similar_user_ids.append(other_user.id)

            if not similar_user_ids:
                return []

            # 유사 사용자 기반 장소 추천
            recommendations = await get_chat_based_recommendations(similar_user_ids, top_n)
            return recommendations or []

        except Exception as e:
            print(f"🚨 [ERROR] 추천 시스템 실패: {str(e)}")
            return []