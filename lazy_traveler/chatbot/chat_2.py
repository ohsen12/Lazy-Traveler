from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.chains import LLMChain
import openai
import os
from dotenv import load_dotenv
from .models import ChatHistory
from django.conf import settings
from datetime import datetime
from django.contrib.auth import get_user_model

User = get_user_model()

persist_dir = os.path.join(settings.BASE_DIR, 'vector_store')

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

embeddings = OpenAIEmbeddings()
vector_store = Chroma(
    persist_directory=persist_dir,  
    embedding_function=embeddings  
)

retriever = vector_store.as_retriever(search_kwargs={"k": 5})

llm = ChatOpenAI(model="gpt-4o-mini")

# ✅ 쿼리 트랜스포메이션용 LLM + 프롬프트 체인
query_transform_prompt = PromptTemplate.from_template("""
다음 사용자 질문을 벡터 검색을 위한 최적화 쿼리로 변환하세요.  
사용자의 위치와 관심 태그를 고려해 간결하고 핵심 키워드를 중심으로 작성합니다.

🔹 사용자 질문: {user_query}  
🔹 위치 정보: {location_context}  
🔹 관심 태그: {tags_context}

👉 최적화된 검색 쿼리:
""")

query_transform_chain = LLMChain(llm=ChatOpenAI(model="gpt-3.5-turbo"), prompt=query_transform_prompt)


# 대화 내역 가져오기
def get_context(session_id, max_turns=5):
    chat_history = ChatHistory.objects.filter(session_id=session_id).order_by("-created_at")[:max_turns]
    return "\n\n".join([f"User: {chat.message}\nBot: {chat.response}" for chat in reversed(chat_history)])


# 유저 태그 가져오기
def get_user_tags(username):
    try:
        user = User.objects.get(username=username)  
        tags = user.tags.split(",") if user.tags else []
        return tags
    except User.DoesNotExist:
        return []


# ✅ Query Transformation → 벡터 검색 수행
def retriever_invoke(user_query, location_context, tags_context):
    try:
        # 1️⃣ 쿼리 변환 수행
        transformed_query = query_transform_chain.predict(
            user_query=user_query,
            location_context=location_context,
            tags_context=tags_context
        )
        print(f"🔧 변환된 검색 쿼리: {transformed_query}")

        # 2️⃣ 변환된 쿼리로 벡터 검색
        docs = retriever.invoke(transformed_query)
        return docs

    except Exception as e:
        print(f"❌ 쿼리 변환 및 검색 오류: {str(e)}")
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

🔍 **사용자 질문**  
{question}

🗂 **참고할 정보 (벡터 DB 검색 결과 및 대화 내역)**  
{context}

📌 만약 벡터 DB에서 관련 정보를 찾지 못하면, 다음과 같이 응답하세요:  
❌ "현재 해당 지역의 정보를 찾을 수 없습니다. 다른 장소를 입력해 주세요!"

**📅 4시간짜리 추천 일정**:
1️⃣ **{time_context} 시작 (첫 장소)**  
2️⃣ 다음 장소  
3️⃣ 마무리 장소
"""
)


# ✅ 메인 추천 함수
def get_recommendation(user_query, session_id=None, username=None, latitude=None, longitude=None):
    try:
        now = datetime.now()
        current_hour = now.hour
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")

        time_of_day = "오전" if current_hour < 12 else "오후" if current_hour < 18 else "저녁"

        if latitude is None or longitude is None:
            latitude, longitude = 37.5704, 126.9831

        user_tags = get_user_tags(username)
        tags_query = " OR ".join(user_tags) if user_tags else ""

        print(f"🔍 현재 세션 ID: {session_id}")
        print(f"🔍 사용자명: {username}")
        print(f"📍 위치: 위도 {latitude}, 경도 {longitude}")
        print(f"🔍 벡터 스토어 경로: {persist_dir}")
        print(f"🔍 벡터 스토어 문서 수: {vector_store._collection.count()}")
        print(f"🔍 사용자 태그: {user_tags}")

        location_context = f"위도 {latitude}, 경도 {longitude}" if latitude and longitude else "위치 정보 없음"
        time_context = f"{current_time}, {time_of_day}"
        tags_context = f"{', '.join(user_tags)}" if user_tags else "관심사 정보 없음"

        # 대화 내역 가져오기
        context = get_context(session_id)

        # ✅ 벡터 검색 → 쿼리 트랜스포메이션 후 검색
        docs = retriever_invoke(
            user_query=user_query,
            location_context=location_context,
            tags_context=tags_context
        )
        print(f"🔍 검색된 문서 수: {len(docs)}")

        if not docs:
            return "❌ 관련 장소 정보를 찾을 수 없습니다. 다른 장소를 입력해 주세요."

        # 검색 결과 + 대화 내역 통합
        context += f"\n{location_context}\n{time_context}\n{tags_context}\n"
        context += "\n".join([doc.page_content for doc in docs])

        # LLM 체인 실행
        chain = prompt | llm

        result = chain.invoke({
            "context": context,
            "location_context": location_context,
            "time_context": time_context,
            "question": user_query
        })

        result_content = result.content
        print("🤖 최종 응답:\n", result_content)

        return result_content

    except Exception as e:
        print(f"❌ 추천 생성 오류: {str(e)}")
        return f"추천 생성 오류: {str(e)}"
