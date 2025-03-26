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
retriever = vector_store.as_retriever(search_kwargs={"k": 10})  # 최대 5개 문서 검색

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
    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # km


# 거리 계산 및 정렬
def sort_places_by_distance(places, latitude, longitude):
    for place in places:
        lat = float(place.metadata.get('latitude', 0))
        lon = float(place.metadata.get('longitude', 0))
        distance = calculate_distance(latitude, longitude, lat, lon)
        place.metadata['distance'] = distance

    return sorted(places, key=lambda x: x.metadata.get('distance', float('inf')))


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

        place = sorted_places[idx].metadata
        schedule.append({
            "time": slot['time'],
            "desc": slot['desc'],
            "name": place.get('name'),
            "category": place.get('category'),
            "address": place.get('address'),
            "distance_km": f"{place.get('distance'):.2f}km",
            "rating": place.get('rating'),
            "website": place.get('website')
        })

    return schedule

def schedule_to_text(schedule):
    """
    스케줄 데이터를 텍스트로 변환해서 LLM에 넘길 수 있도록 준비
    """
    lines = []
    for place in schedule:
        lines.append(f"""
⏰ {place['time']} - {place['desc']}
- 장소: **{place['name']}**
- 카테고리: {place['category']}
- 주소: {place['address']}
- 거리: {place['distance_km']}
- 평점: {place['rating']}
- 웹사이트: {place['website']}
        """)
    return "\n".join(lines)


CATEGORY_MAPPING = {
    "볼거리": ["박물관", "서점", "미술관", "공원", "관광명소", "쇼핑", "옷"],
    "먹을거리": ["베이커리", "베트남 음식", "브런치", "비건", "양식", "일식", "중식", "태국 음식", "피자", "한식", "햄버거"],
    "아침식사": ["한식", "비건", "브런치"],
    "야식": ["주점", "피자", "햄버거", "중식"],
    "카페": ["카페", "브런치", "베이커리"]
}

def build_schedule_by_categories(sorted_places, schedule_categories, start_time):
    schedule = []
    used_place_ids = set()

    time_slots = [
        (start_time + timedelta(hours=i)).strftime("%H:%M") for i in range(len(schedule_categories))
    ]

    for i, category in enumerate(schedule_categories):
        for place in sorted_places:
            metadata = place.metadata
            if metadata.get('place_id') in used_place_ids:
                continue  # 이미 사용한 장소 패스

            if category in CATEGORY_MAPPING and metadata.get('category') in CATEGORY_MAPPING[category]:
                used_place_ids.add(metadata.get('place_id'))
                schedule.append({
                    "time": time_slots[i],
                    "desc": category,
                    "name": metadata.get('name'),
                    "category": metadata.get('category'),
                    "address": metadata.get('address'),
                    "distance_km": f"{metadata.get('distance', 0):.2f}km",
                    "rating": metadata.get('rating'),
                    "website": metadata.get('website')
                })
                break

    return schedule

def map_tags_to_categories(user_tags):
    mapped_categories = set()

    if not user_tags:
        return list(CATEGORY_MAPPING.keys()) # 반환

    for category, tags in CATEGORY_MAPPING.items():
        for tag in user_tags:
            if tag in tags:
                mapped_categories.add(category)
                break  # 중복 방지

    return list(mapped_categories)


def determine_schedule_template(current_time):
    hour = current_time.hour

    # 오후 11시 ~ 오전 7시 59분까지는 스케줄링 불가
    if hour >= 23 or hour < 8:
        return "불가시간", ["지금은 스케줄링이 어려워요. 익일 오전 8:00 일정부터 스케줄링을 시작할까요?"]

    # 오전 8시 ~ 오전 8시 59분
    if 8 <= hour < 9:
        return "아침", ["아침 식사", "볼거리", "볼거리", "먹을거리"]
    # 오전 9시 ~ 오전 9시 59분
    if 9 <= hour < 10:
        return "아침", ["아침 식사", "볼거리", "볼거리", "먹을거리"]
    # 오전 10시 ~ 오전 10시 59분
    if 10 <= hour < 11:
        return "점심", ["먹을거리", "볼거리", "카페", "볼거리"]
    # 오전 11시 ~ 오후 12시 59분
    if 11 <= hour < 14:
        return "점심", ["먹을거리", "볼거리", "카페", "볼거리"]
    # 오후 1시 ~ 오후 1시 59분
    if 13 <= hour < 14:
        return "점심", ["먹을거리", "볼거리", "카페", "볼거리"]
    # 오후 2시 ~ 오후 2시 59분
    if 14 <= hour < 15:
        return "오후", ["볼거리", "카페", "볼거리", "볼거리"]
    # 오후 3시 ~ 오후 3시 59분
    if 15 <= hour < 16:
        return "오후", ["볼거리", "카페", "볼거리", "먹을거리"]
    # 오후 4시 ~ 오후 4시 59분
    if 16 <= hour < 17:
        return "오후 후반", ["볼거리", "카페", "먹을거리", "볼거리"]
    # 오후 5시 ~ 오후 5시 59분
    if 17 <= hour < 18:
        return "저녁 전", ["먹을거리", "볼거리", "볼거리", "야식"]
    # 오후 6시 ~ 오후 6시 59분
    if 18 <= hour < 19:
        return "저녁", ["먹을거리", "볼거리", "볼거리", "야식"]
    # 오후 7시 ~ 오후 7시 59분
    if 19 <= hour < 20:
        return "저녁 후반", ["먹을거리", "볼거리", "야식", "야식"]
    # 오후 8시 ~ 오후 8시 59분 (남은 시간이 3시간)
    if 20 <= hour < 21:
        return "야간 초반", ["볼거리", "야식", "야식"]
    # 오후 9시 ~ 오후 9시 59분 (남은 시간이 2시간)
    if 21 <= hour < 22:
        return "야간 중반", ["야식", "야식"]
    # 오후 10시 ~ 오후 10시 59분 (남은 시간이 1시간)
    if 22 <= hour < 23:
        return "야간 후반", ["야식"]

    # 기본값 (예외)
    return "기본", ["먹을거리", "볼거리", "카페", "볼거리"]


function_vector_store = Chroma(
    collection_name="function_collection",
    embedding_function=embeddings,
    persist_directory=persist_dir
)

place_vector_store = Chroma(
    collection_name="place_collection",
    embedding_function=embeddings,
    persist_directory=persist_dir
)

def classify_question_with_vector(user_query, threshold=0.7):

    function_results = function_vector_store.similarity_search_with_score(
        query=user_query,
        k=1,
        filter={"type": "qa"}
    )

    place_results = place_vector_store.similarity_search_with_score(
        query=user_query,
        k=1,
        filter={"type": "place"}
    )

    function_score = function_results[0][1] if function_results else 0
    place_score = place_results[0][1] if place_results else 0

    print(f"[DEBUG] function_score: {function_score}, place_score: {place_score}")


    if function_score <= place_score:
        return "function"
    elif place_score <= function_score:
        return "place"
    return "place"


function_prompt = ChatPromptTemplate.from_template("""
당신은 LazyTraveler 서비스의 기능에 대해 설명하는 전문 AI 챗봇입니다.

아래의 규칙을 반드시 따릅니다.

🔹 **질문 분석 및 답변 규칙**
1. 사용자의 질문은 '기능 질문'입니다.
2. 기능 설명은 친절하고 명확하게 작성합니다.
3. 질문과 관련된 기능 외에는 답변하지 않습니다.
4. 제공하는 정보는 반드시 벡터DB 검색 결과 또는 아래 참고 정보만 사용합니다.

🔍 **사용자 질문**
{question}

🗂 **참고할 정보 (벡터 DB 검색 결과 및 대화 내역)**
{context}

예시)
- 회원가입은 어떻게 하나요?
- 내 태그를 수정하고 싶어요.
- 이전에 했던 대화를 확인하고 싶어요.
""")

place_prompt = ChatPromptTemplate.from_template("""
당신은 지역 기반 맛집과 관광지를 추천하는 전문 AI 챗봇입니다.

🔹 **답변 규칙**
1. 반드시 제공된 추천 일정 데이터를 기반으로만 답변합니다.
2. 장소 이름, 카테고리, 주소, 거리, 평점 등의 정보를 정확하게 포함해 설명합니다.
3. 장소 외 다른 정보나 기능 설명은 하지 않습니다.
4. 장소가 충분하지 않을 경우 "추천할 장소가 부족합니다."라고 답변합니다.

🗂 **추천 일정 데이터**
{context}

📍 **사용자 현재 위치**: {location_context}
⏰ **현재 시간**: {time_context}

🔍 **사용자 질문**
{question}
""")


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

"""
)



def get_recommendation(user_query, session_id=None, username=None, latitude=None, longitude=None):


    # now = datetime.now()
    now = datetime(2024, 3, 27, 9, 30, 0)
    # current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    start_time = now

    if latitude is None or longitude is None:
        latitude, longitude = 37.5704, 126.9831

    question_type = classify_question_with_vector(user_query)

    if question_type == "function":
        # 기능 벡터DB에서 검색된 문서 가져오기
        function_docs = function_vector_store.similarity_search(user_query, k=3)

        # 벡터 검색 결과가 없을 경우 예외처리
        if not function_docs:
            return "기능 관련 정보를 찾을 수 없습니다."

        # 문서 내용을 context로 준비
        function_context = "\n".join([doc.page_content for doc in function_docs])

        # 기능용 프롬프트 + LLM 체인 호출
        chain = function_prompt | llm

        result = chain.invoke({
            "context": function_context,
            "question": user_query
        })

        return result.content.strip() if result.content else "기능 관련 답변을 제공할 수 없습니다."

    # 태그 가져오기
    user_tags = get_user_tags(username)
    categories = map_tags_to_categories(user_tags)

    schedule_type, categories = determine_schedule_template(now)
    if schedule_type == "불가시간":
        return "스케줄링 불가시간입니다."
    
    # 문서 검색
    search_query = f"{user_query} (위치: {latitude}, {longitude}) 관련 태그: {categories}"

    docs = retriever.invoke(search_query)

    # 거리 정렬
    sorted_docs = sort_places_by_distance(docs, latitude, longitude)
    print(sorted_docs)

    schedule = build_schedule_by_categories(sorted_docs, categories, start_time)

    # 5. 스케줄을 텍스트로 변환
    schedule_text = schedule_to_text(schedule)

    # # 스케줄 생성
    # schedule = build_schedule(sorted_docs, start_time)

    # # 스케줄 텍스트 변환
    # schedule_text = schedule_to_text(schedule)

    # 기존 컨텍스트에 추가
    context = get_context(session_id)
    context += f"\n{schedule_text}"

    # ✅ LLM 모델 설정
    chain = place_prompt | llm

    # LLM 호출
    result = chain.invoke({
        "context": context,
        "location_context": f"현재 사용자의 위치는 위도 {latitude}, 경도 {longitude}입니다.",
        "time_context": f"현재 시간은 {now}입니다.",
        "question": user_query
    })

    return result.content.strip() if result.content else "추천을 제공할 수 없습니다."
