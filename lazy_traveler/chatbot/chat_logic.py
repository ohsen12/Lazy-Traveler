from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from datetime import timedelta
import math
import openai
import os
from dotenv import load_dotenv
from .models import ChatHistory  
from django.conf import settings
from datetime import datetime
from django.contrib.auth import get_user_model
User = get_user_model()

# persist_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'vector')

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
retriever = vector_store.as_retriever(search_kwargs={"k": 5})  # 최대 10개 문서 검색

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
        tags = user.tags if user.tags else ""
        return tags
    except User.DoesNotExist:
        return ""
   
# 거리 계산 함수
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # km


# 거리 계산 및 정렬
def sort_places_by_distance(places, user_lat, user_lon):
    for place in places:
        lat = float(place['metadata'].get('latitude', 0))
        lon = float(place['metadata'].get('longitude', 0))
        distance = calculate_distance(user_lat, user_lon, lat, lon)
        place['distance'] = distance

    return sorted(places, key=lambda x: x['distance'])

def build_schedule(sorted_places, start_time):
    """
    4시간짜리 일정 생성 (장소 리스트 기반)
    """
    schedule = []
    time_slots = [
        {"desc": "시작 장소 (주로 식사 또는 카페)", "time": start_time.strftime("%H:%M")},
        {"desc": "주요 방문 장소 (관광지, 명소)", "time": (start_time + timedelta(hours=1)).strftime("%H:%M")},
        {"desc": "추가 장소 (카페, 쇼핑 등)", "time": (start_time + timedelta(hours=2)).strftime("%H:%M")},
        {"desc": "마무리 장소 (다시 식사 또는 간식)", "time": (start_time + timedelta(hours=3)).strftime("%H:%M")},
    ]

    for idx, slot in enumerate(time_slots):
        if idx >= len(sorted_places):
            break

        place = sorted_places[idx]['metadata']
        schedule.append({
            "time": slot['time'],
            "desc": slot['desc'],
            "name": place.get('name'),
            "category": place.get('category'),
            "address": place.get('address'),
            "distance_km": f"{sorted_places[idx]['distance']:.2f}km",
            "rating": place.get('rating'),
            "website": place.get('website')
        })

    return schedule



prompt = ChatPromptTemplate.from_template(
    """
    
당신은 지역 기반 맛집과 관광지를 추천하는 전문 AI 챗봇입니다.
사용자의 질문을 정확히 이해하고, 벡터 DB에서 검색한 정보를 바탕으로 신뢰할 수 있는 답변을 제공합니다.

🔹 **질문 분석 및 답변 규칙**
1. **질문 유형을 먼저 파악하세요**:
   - '기능 질문' (챗봇 기능 또는 시스템 관련 질문)
   - '맛집 추천' (지역 기반 식당 추천 요청)
   - '관광지 추천' (방문할 장소 추천 요청)
   
2. **기능 질문 키워드**:
   - 회원가입, 가입 방법, 가입절차, 추천 기준, 공유, 내 정보, 대화 기록, 태그, 위치 추천, 회원탈퇴, 재가입, 회원 정보 조회, 회원 정보 수정, 지난 대화, 대화내역, 관심사, 답변
   - 위 키워드가 포함된 질문이면 기능 질문으로 분류하세요.

3. **기능 질문이면 해당 답변만 제공**
   - 기능 질문으로 분류된 경우, 맛집 및 관광지 추천 없이 기능 관련 답변만 제공합니다.
   - 답변은 벡터DB에서 찾은 정보만 제공합니다.

4. **정확한 정보만 제공**: 벡터 DB에서 찾은 정보만 사용하세요.
5. **사용자의 현재 위치 고려**:
   - 현재 위치 정보: {location_context}
   - 위치 정보가 없으면 기본 지역(서울 종로구) 기준으로 추천하세요.
6. **시간 기반 추천 제공**:
   - 현재 시간: {time_context}
   - 특정 시간을 언급한 경우 해당 시간에 맞는 일정을 추천하세요.

🔍 **사용자 질문**
{question}

🗂 **참고할 정보 (벡터 DB 검색 결과 및 대화 내역)**
{context}


---

**[질의 시각에 따른 일정 추천]**
{time_context}
1️⃣ **현재 시간이 오전 8:00 ~ 오후 11:00 사이일 때:**
    - 사용자가 특정 시간을 지정하면, 해당 시간에 맞는 일정을 생성하세요.
    - 사용자가 시간을 지정하지 않으면 현재 시간을 기준으로 4시간 일정을 추천하세요.

2️⃣ **추천 일정 예시:**
- **오전 8:00 ~ 오전 8:59**: [아침 식사 > 볼거리 > 볼거리 > 먹을거리]
- **오후 12:00 ~ 오후 12:59**: [먹을거리 > 볼거리 > 카페 > 볼거리]
- **오후 7:00 ~ 오후 7:59**: [먹을거리 > 볼거리 > 야식 > 야식]
- **오후 10:00 ~ 오후 10:59**: [야식] (오후 11시까지만 추천)

---

**📅 일정 템플릿**

1️⃣ **{time_context} ~ {time_context} : (질문 시간 기준, 대분류 > 태그 첫 장소)**
   - 장소: **[장소 이름]**
   - 위치: 현재 설정된 위치로부터 거리
   - 평점:
   - 영업시간:
   - 웹사이트:
"""
)



def get_recommendation(user_query, session_id=None, username=None, latitude=None, longitude=None):
    try:
      #   # ✅ 벡터 DB에서 유사한 질문 찾기 (유사도 확인만)
      #   results = vector_store.similarity_search_with_relevance_scores(user_query, k=3)

      #   # ✅ 유사도 기준 필터링 
      #   relevant_answers = [res.metadata.get('answer', 'Unknown answer') for res, score in results]

      #    # ✅ 만약 유사한 질문이 없으면 기본 응답 추가
      #   if not relevant_answers:
      #       relevant_answers.append("해당 질문에 대한 정보가 없습니다. 다시 질문해 주세요.")

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
      #   context += "\n".join(relevant_answers)  # 유사도 높은 답변도 같이 전달
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


