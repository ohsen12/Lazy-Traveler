from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
import openai
import os
from dotenv import load_dotenv
from .models import ChatHistory  
from django.conf import settings
from langchain.schema import AIMessage
from datetime import datetime
from django.contrib.auth import get_user_model
User = get_user_model()

persist_dir = os.path.join(settings.BASE_DIR, 'vector_store')

# .env 파일 로드
load_dotenv()

# API key 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ vector_store.py에서 생성한 벡터 DB 불러오기
embeddings = OpenAIEmbeddings()
vector_store = Chroma(
    persist_directory=persist_dir,  
    embedding_function=embeddings  
)

# 벡터 검색기 설정
retriever = vector_store.as_retriever(search_kwargs={"k": 10})  # 최대 10개 문서 검색

# LLM 설정
llm = ChatOpenAI(model="gpt-4o-mini")

# 대화 내역을 가져오는 함수
def get_context(session_id, max_turns=5):
    chat_history = ChatHistory.objects.filter(session_id=session_id).order_by("-created_at")[:max_turns]
    return "\n\n".join([f"User: {chat.message}\nBot: {chat.response}" for chat in reversed(chat_history)])

# 유저 태그 가져오기
def get_user_tags(username):
    try:
        # 현재 세션에 해당하는 사용자 찾기
        user = User.objects.get(username=username)  
        tags = user.tags.split(",") if user.tags else []
        return tags
    except User.DoesNotExist:
        return []


# 프롬프트 정의
prompt = ChatPromptTemplate.from_template(
    """
    당신은 지역 기반 맛집과 관광지를 추천하는 전문 AI 챗봇입니다.
    사용자의 질문을 이해하고, 벡터 DB에서 검색한 정보를 바탕으로 신뢰할 수 있는 4시간짜리 일정을 제공합니다.

    🔹 **답변 규칙**
    1. **정확한 정보만 제공**: 벡터 DB에서 찾은 정보만 사용하세요.
    2. **사용자의 현재 위치 고려**:  
       {location_context}
    3. **현재 시간 기반 추천 (총 4시간 일정 구성)**:  
       {time_context}
       - **추천 일정** (현재 시간 기준 4시간짜리 스케줄)
         1. 시작 장소: 주로 맛집 (식사 또는 카페)
         2. 주요 방문 장소: 관광지, 명소, 체험 활동
         3. 추가 장소: 카페, 쇼핑, 휴식 공간
         4. 마무리 장소: 다시 식사(또는 간식)할 곳

    🔍 **사용자 질문**  
    {question}

    🗂 **참고할 정보 (벡터 DB 검색 결과 및 대화 내역)**  
    {context}

    📌 만약 벡터 DB에서 관련 정보를 찾지 못하면, 다음과 같이 응답하세요:  
    ❌ "현재 해당 지역의 정보를 찾을 수 없습니다. 다른 장소를 입력해 주세요!"  

**📅 4시간짜리 추천 일정**:

1️⃣ **{time_context} 시작 (현재 시간 기준 첫 장소)**
   - 장소: **[장소 이름]**
   - 추천 이유: 
   - 위치: 현재 설정된 위치로부터 거리
   - 평점: 
   - 영업시간: 
   - 웹사이트: 

2️⃣ **다음 장소 (1~2시간 후 방문)**
   - 장소: **[장소 이름]**
   - 추천 이유: 
   - 위치: 현재 설정된 위치로부터 거리
   - 평점: 
   - 영업시간: 
   - 웹사이트: 

3️⃣ **마무리 장소 (마지막 30~60분)**
   - 장소: **[장소 이름]**
   - 추천 이유: 
   - 위치: 현재 설정된 위치로부터 거리
   - 평점: 
   - 영업시간: 
   - 웹사이트: 


---
"""
)



def get_recommendation(user_query, session_id=None, username=None, latitude=None, longitude=None):
    try:
        # 현재 시간 가져오기
        now = datetime.now()
        current_hour = now.hour
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")

        time_of_day = "오전" if current_hour < 12 else "오후" if current_hour < 18 else "저녁"

        # 기본 위치 설정 (종각역)
        if latitude is None or longitude is None:
            latitude, longitude = 37.5704, 126.9831

        # 사용자의 tags 가져오기
        user_tags = get_user_tags(username)
        tags_query = " OR ".join(user_tags) if user_tags else ""

        print(f"🔍 현재 세션 ID: {session_id}")
        print(f"🔍 현재 사용자명: {username}")
        print(f"📍 현재 위치: 위도 {latitude}, 경도 {longitude}")
        print(f"🔍 벡터 스토어 절대경로: {persist_dir}")
        print(f"🔍 현재 벡터 스토어에 저장된 문서 개수: {vector_store._collection.count()}")
        print(f"🔍 사용자 관심 태그: {user_tags}")

        # 위치 & 시간 정보
        location_context = f"현재 사용자의 위치는 위도 {latitude}, 경도 {longitude} 입니다." if latitude and longitude else "사용자의 위치 정보가 없습니다."
        time_context = f"현재 시간은 {current_time}이며, {time_of_day}입니다."
        tags_context = f"사용자는 다음과 같은 관심사를 가지고 있습니다: {', '.join(user_tags)}" if user_tags else "사용자의 관심사 정보가 없습니다."

        # 대화 내역 가져오기
        context = get_context(session_id)

        # 벡터 DB에서 관련 문서 검색 (tags 반영)
        search_query = f"{user_query} (위치: {latitude}, {longitude}, 시간: {time_of_day}) 태그: {tags_query}"
        docs = retriever.invoke(search_query)
        print(f"🔍 검색된 관련 문서 개수: {len(docs)}")

        if not docs:
            return "죄송합니다, 관련된 장소 정보를 찾을 수 없습니다."

        # 벡터 DB에서 찾은 문서와 기존 대화 내역을 결합
        context += f"\n{location_context}\n{time_context}\n{tags_context}\n" + "\n".join([doc.page_content for doc in docs])

        # LLM 모델 설정
        chain = prompt | llm

        # 템플릿에 context, location_context, time_context, user_query 전달
        result = chain.invoke({"context": context, "location_context": location_context, "time_context": time_context, "question": user_query})

        # LLM의 응답 내용 가져오기
        result_content = result.content

        print("🤖 LLM의 최종 응답:\n", result_content)
        return result_content

    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return f"추천을 생성하는 중 오류 발생: {str(e)}"