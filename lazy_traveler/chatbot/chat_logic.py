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

persist_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'vector')

# .env 파일 로드
load_dotenv()

# API key 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# settings.BASE_DIR의 경로가 올바르게 설정되어 있는지 확인
persist_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'vector_2')

# 경로가 존재하는지 확인하고, 없으면 생성
if not os.path.exists(persist_dir):
    os.makedirs(persist_dir)

# embeddings 도구 설정
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Chroma DB 로드
vector_store = Chroma(
    collection_name="combined_collection",
    embedding_function=embeddings,
    persist_directory=persist_dir
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


prompt = ChatPromptTemplate.from_template(
    """
    당신은 지역 기반 맛집과 관광지를 추천하는 전문 AI 챗봇입니다.
    사용자의 질문을 이해하고, 벡터 DB에서 검색한 정보를 바탕으로 신뢰할 수 있는 답변을 제공합니다.

    🔹 **답변 규칙**
    1. **정확한 정보만 제공**: 벡터 DB에서 찾은 정보만 사용하세요.
    2. **사용자의 현재 위치 고려**:  
       {location_context}
    3. **기능 관련 질문에도 답변 가능**: 사용자가 시스템이나 기능 관련 질문을 하면, 적절한 설명을 제공하세요.

    🔍 **사용자 질문**  
    {question}

    🗂 **참고할 정보 (벡터 DB 검색 결과 및 대화 내역)**  
    {context}

    📌 만약 벡터 DB에서 관련 정보를 찾지 못하면, 다음과 같이 응답하세요:  
    ❌ "현재 해당 정보가 없습니다. 다른 질문을 입력해 주세요!"

    ---

    **📅 4시간짜리 추천 일정**:

    **[질의 시각에 따른 일정 추천]**
    {time_context}
    1️⃣ **현재 시간이 오전 8:00 ~ 오후 11:00 사이일 때:**

        1. **오후 11:00 ~ 오전 7:59**:  
           [지금은 스케줄링이 어려워요. 익일 오전 8:00 일정부터 스케줄링을 시작할까요?]

        2. **오전 8:00 ~ 오전 8:59**:  
           [아침 식사 > 볼거리 > 볼거리 > 먹을거리] 추천

        3. **오전 9:00 ~ 오전 9:59**:  
           [아침 식사 > 볼거리 > 볼거리 > 먹을거리] 추천

        4. **오전 10:00 ~ 오전 10:59**:  
           [먹을거리 > 볼거리 > 카페 > 볼거리] 추천

        5. **오전 11:00 ~ 오전 11:59**:  
           [먹을거리 > 볼거리 > 카페 > 볼거리] 추천

        6. **오후 12:00 ~ 오후 12:59**:  
           [먹을거리 > 볼거리 > 카페 > 볼거리] 추천

        7. **오후 1:00 ~ 오후 1:59**:  
           [먹을거리 > 볼거리 > 카페 > 볼거리] 추천

        8. **오후 2:00 ~ 오후 2:59**:  
           [볼거리 > 카페 > 볼거리 > 볼거리] 추천

        9. **오후 3:00 ~ 오후 3:59**:  
           [볼거리 > 카페 > 볼거리 > 먹을거리] 추천

        10. **오후 4:00 ~ 오후 4:59**:  
           [볼거리 > 카페 > 먹을거리 > 볼거리] 추천

        11. **오후 5:00 ~ 오후 5:59**:  
           [먹을거리 > 볼거리 > 볼거리 > 야식] 추천

        12. **오후 6:00 ~ 오후 6:59**:  
           [먹을거리 > 볼거리 > 볼거리 > 야식] 추천

        13. **오후 7:00 ~ 오후 7:59**:  
           [먹을거리 > 볼거리 > 야식 > 야식] 추천 (동일 야식 카테고리에서 주점이 가장 늦게 추천될 수 있을까요?)

        14. **오후 8:00 ~ 오후 8:59**:  
           [볼거리 > 야식 > 야식] 추천 (오후 8:00 기준으로 11시까지만 추천되므로, 3시간만 추천되어야 합니다)

        15. **오후 9:00 ~ 오후 9:59**:  
           [야식 > 야식] 추천 (오후 9:00 기준으로 11시까지만 추천되므로, 2시간만 추천되어야 합니다)

        16. **오후 10:00 ~ 오후 10:59**:  
           [야식] 추천 (오후 10:00 기준으로 11시까지만 추천되므로, 1시간만 추천되어야 합니다)

    ---

    **📅 일정 템플릿**

    1️⃣ **{time_context} ~ {time_context} : (질의 시간 기준, 대분류 > 태그 첫 장소)**
       - 장소: **[장소 이름]**
       - 위치: 현재 설정된 위치로부터 거리
       - 평점: 
       - 영업시간: 
       - 웹사이트: 
    """
)






def get_recommendation(user_query, session_id=None, username=None, latitude=None, longitude=None):
    try:
        # ✅ 벡터 DB에서 유사한 질문 찾기 (유사도 확인만)
        results = vector_store.similarity_search_with_relevance_scores(user_query, k=3)

        # ✅ 유사도 기준 필터링 (예: 0.7 이상만 포함)
        relevant_answers = [res.metadata.get('answer', 'Unknown answer') 
                            for res, score in results]

         # ✅ 만약 유사한 질문이 없으면 기본 응답 추가
        if not relevant_answers:
            relevant_answers.append("해당 질문에 대한 정보가 없습니다. 다시 질문해 주세요.")

         # ✅ 현재 시간 & 위치 정보 설정
        now = datetime.now()
        current_hour = now.hour
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        time_of_day = "오전" if current_hour < 12 else "오후" if current_hour < 18 else "저녁"

        if latitude is None or longitude is None:
            latitude, longitude = 37.5704, 126.9831  # 기본 위치 (종각역)

        # ✅ 유저 태그 가져오기
        user_tags = get_user_tags(username)
        tags_query = " OR ".join(user_tags) if user_tags else None
        tags_context = f"사용자의 관심사: {', '.join(user_tags)}" if user_tags else "사용자의 관심사 정보 없음."

        # ✅ 대화 내역 가져오기
        context = get_context(session_id)

        # ✅ 장소 정보 검색 (태그 반영)
        search_query = f"{user_query} (위치: {latitude}, {longitude}, 시간: {time_of_day})"
        if tags_query:
            search_query += f" 태그: {tags_query}"

        try:
            docs = retriever.invoke(search_query)
        except Exception as e:
            print(f"문서 검색 중 오류 발생: {str(e)}")
            docs = []

        print(f"🔍 검색된 관련 문서 개수: {len(docs)}")

        # ✅ 벡터 DB에서 찾은 문서들을 LLM에게 전달
        context += f"\n{tags_context}\n"
        context += f"현재 위치: 위도 {latitude}, 경도 {longitude}\n"
        context += f"현재 시간: {current_time}, {time_of_day}\n"
        context += "\n".join(relevant_answers)  # 유사도 높은 답변도 같이 전달
        context += "\n".join([doc.page_content for doc in docs])  # 장소 정보 추가

        # ✅ LLM 모델 설정
        chain = prompt | llm

        # ✅ LLM 실행
        result = chain.invoke({
            "context": context,
            "location_context": f"현재 사용자의 위치는 위도 {latitude}, 경도 {longitude} 입니다.",
            "time_context": f"현재 시간은 {current_time}이며, {time_of_day}입니다.",
            "question": user_query
        })

        # ✅ LLM 응답 반환
        result_content = result.content.strip() if result.content else "죄송합니다, 유효한 추천을 제공할 수 없습니다. 다시 시도해 주세요."
        print("🤖 LLM의 최종 응답:\n", result_content)
        return result_content

    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return f"추천을 생성하는 중 오류 발생: {str(e)}"


