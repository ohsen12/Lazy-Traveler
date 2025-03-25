import math
from .models import ChatHistory
from django.contrib.auth import get_user_model
from datetime import timedelta
from .openai_chroma_config import function_vector_store, place_vector_store
from asgiref.sync import sync_to_async

User = get_user_model()

# 대화 내역을 가져오는 함수
@sync_to_async
def get_context(session_id, max_turns=5):
    chat_history = ChatHistory.objects.filter(session_id=session_id).order_by("-created_at")[:max_turns]
    return "\n\n".join([f"User: {chat.message}\nBot: {chat.response}" for chat in reversed(chat_history)])

# 유저 태그 가져오기
@sync_to_async
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
@sync_to_async
def sort_places_by_distance(places, latitude, longitude):
    for place in places:
        lat = float(place.metadata.get('latitude', 0))
        lon = float(place.metadata.get('longitude', 0))
        distance = calculate_distance(latitude, longitude, lat, lon)
        place.metadata['distance'] = distance

    return sorted(places, key=lambda x: x.metadata.get('distance', float('inf')))

# 스케줄 LLM전 정제
@sync_to_async
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

#카테고리 대분류
CATEGORY_MAPPING = {
    "볼거리": ["박물관", "서점", "미술관", "공원", "관광명소", "쇼핑", "옷"],
    "먹을거리": ["베이커리", "베트남 음식", "브런치", "비건", "양식", "일식", "중식", "태국 음식", "피자", "한식", "햄버거"],
    "아침식사": ["한식", "비건", "브런치"],
    "야식": ["주점", "피자", "햄버거", "중식"],
    "카페": ["카페", "브런치", "베이커리"]
}

# 카테고리별 스케줄
@sync_to_async
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

#태그데이터 대분류로 변경
@sync_to_async
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

#대분류 일정 스케줄링
@sync_to_async
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

#어떤 질문인지 파악
@sync_to_async
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

    if function_score < place_score:
        return "function"
    else:
        return "place"