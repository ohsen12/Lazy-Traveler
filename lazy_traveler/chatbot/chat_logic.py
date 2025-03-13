from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import openai
import os
import traceback  
from dotenv import load_dotenv
from .models import ChatHistory  
from django.conf import settings
from langchain.schema import AIMessage
from datetime import datetime, timedelta

persist_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'vector_store')

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
retriever = vector_store.as_retriever()

# LLM 설정
llm = ChatOpenAI(model="gpt-4o-mini")

# 대화 내역을 가져오는 함수
def get_context(session_id, max_turns=5):
    chat_history = ChatHistory.objects.filter(session_id=session_id).order_by("-created_at")[:max_turns]
    return "\n\n".join([f"User: {chat.message}\nBot: {chat.response}" for chat in reversed(chat_history)])




# 프롬프트 정의
prompt = ChatPromptTemplate.from_template(
    """
    당신은 지역 기반 맛집과 관광지를 추천하는 전문 AI 챗봇입니다.
    사용자의 질문을 이해하고, 벡터 DB에서 검색한 정보를 바탕으로 신뢰할 수 있는 추천을 제공합니다.

    🔹 **답변 규칙**
    1. **정확한 정보만 제공**: 벡터 DB에서 찾은 정보만 사용하세요.
    2. **사용자의 현재 위치 고려**: 
       {location_context}
    3. **일정 기반 추천**: 현재 시간 기준으로 오전, 오후, 저녁에 맞는 먹을거리 및 볼거리를 스케줄링하세요.
       - **먹을거리**: 
         - 식사 카테고리는 1시간 소요
         - 카페 카테고리는 2시간 소요
       - **볼거리**: 관광 카테고리는 2시간 소요


    🔍 **사용자 질문**  
    {question}

    🗂 **참고할 정보 (벡터 DB 검색 결과 및 대화 내역)**  
    {context}

    📌 만약 벡터 DB에서 관련 정보를 찾지 못하면, 다음과 같이 응답하세요:  
    ❌ "현재 해당 지역의 정보를 찾을 수 없습니다. 다른 장소를 입력해 주세요!"  
    """
)


def get_recommendation(user_query, session_id, latitude=None, longitude=None):
    try:
        # 기본 위치 설정 (종각역)
        if latitude is None or longitude is None:
            latitude, longitude = 37.5704, 126.9831
        
        print(f"🔍 현재 세션 ID: {session_id}")
        print(f"📍 현재 위치: 위도 {latitude}, 경도 {longitude}")
        print(f"🔍 벡터 스토어 절대경로: {persist_dir}")
        print(f"🔍 현재 벡터 스토어에 저장된 문서 개수: {vector_store._collection.count()}")

        # 위치 정보를 프롬프트에 추가
        location_context = f"현재 사용자의 위치는 위도 {latitude}, 경도 {longitude} 입니다." if latitude and longitude else "사용자의 위치 정보가 없습니다."
        
        # 대화 내역 가져오기
        context = get_context(session_id)

        # 벡터 DB에서 관련 문서 검색
        docs = retriever.invoke(user_query)
        print(f"🔍 검색된 관련 문서 개수: {len(docs)}")

        if not docs:
            return "죄송합니다, 관련된 장소 정보를 찾을 수 없습니다."

        # 벡터 DB에서 찾은 문서와 기존 대화 내역을 결합
        context += f"\n{location_context}\n" + "\n".join([doc.page_content for doc in docs])

        # LLM 모델 설정
        chain = prompt | llm

        # 템플릿에 context, location_context, user_query 전달
        result = chain.invoke({"context": context, "location_context": location_context, "question": user_query})

        # 응답 파싱 (AIMessage 객체인지 확인 후 처리)
        result_content = result.content if isinstance(result, AIMessage) else str(result)
        
        print("🤖 LLM의 최종 응답:\n", result_content)
        return result_content

    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return f"추천을 생성하는 중 오류 발생: {str(e)}"
