import math
import random
from .models import ChatHistory
from django.contrib.auth import get_user_model
from datetime import timedelta
from .openai_chroma_config import function_vector_store, place_vector_store
from asgiref.sync import sync_to_async
from langchain.chains import LLMChain
from .prompt import query_prompt
from .openai_chroma_config import llm

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
    "볼거리": ["공원", "관광명소", "전시","서점"],
    "맛집": ["베이커리", "베트남 음식", "브런치", "비건", "양식", "일식", "중식", "태국 음식", "피자", "한식", "햄버거"],
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
        print(f"\n[DEBUG] 현재 요청된 대분류 카테고리: {category}")
        
        for place in sorted_places:
            metadata = place.metadata
            raw_category = metadata.get('category', '').strip()
            print(f"[DEBUG] 장소: {metadata.get('name')} / category: {raw_category}")

            if metadata.get('place_id') in used_place_ids:
                continue

            if category in CATEGORY_MAPPING:
                for tag in CATEGORY_MAPPING[category]:
                    if tag in raw_category:
                        print(f"[MATCH] {raw_category} ← {tag} (category: {category})")
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

            else:
                print(f"[NO MATCH] {raw_category}는 CATEGORY_MAPPING에 정의되지 않음")

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

    # 오전 8시 ~ 오전 9시 59분
    if 8 <= hour < 10:
        return "아침", ["아침 식사", "볼거리", "볼거리", "맛집"]
    # 오전 10시 ~ 오전 1시 59분
    if 10 <= hour < 14:
        return "점심", ["맛집", "볼거리", "카페", "볼거리"]
    # 오후 2시 ~ 오후 2시 59분
    if 14 <= hour < 15:
        return "오후", ["볼거리", "카페", "볼거리", "볼거리"]
    # 오후 3시 ~ 오후 3시 59분
    if 15 <= hour < 16:
        return "오후", ["볼거리", "카페", "볼거리", "맛집"]
    # 오후 4시 ~ 오후 4시 59분
    if 16 <= hour < 17:
        return "오후 후반", ["볼거리", "카페", "맛집", "볼거리"]
    # 오후 5시 ~ 오후 6시 59분
    if 17 <= hour < 19:
        return "저녁 전", ["맛집", "볼거리", "볼거리", "야식"]
    # 오후 7시 ~ 오후 7시 59분
    if 19 <= hour < 20:
        return "저녁 후반", ["맛집", "볼거리", "야식", "야식"]
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
    return "기본", ["맛집", "볼거리", "카페", "볼거리"]


#어떤 질문인지 파악
# @sync_to_async
# def classify_question_with_vector(user_query, threshold=1.3):

#     function_results = function_vector_store.similarity_search_with_score(
#         query=user_query,
#         k=1,
#         filter={"type": "qa"}
#     )

#     place_results = place_vector_store.similarity_search_with_score(
#         query=user_query,
#         k=1,
#         filter={"type": "place"}
#     )

#     function_score = function_results[0][1] if function_results else 0
#     place_score = place_results[0][1] if place_results else 0

#     if function_score < place_score:
#         return "function"
#     else:
#         return "place"
    
@sync_to_async
def get_preferred_tags_by_schedule(user_tags, schedule_categories):

    result = {}
    for category in schedule_categories:
        default_subcategories = CATEGORY_MAPPING.get(category, [])
        preferred = [tag for tag in default_subcategories if tag in user_tags]

        result[category] = preferred if preferred else default_subcategories

    return result

@sync_to_async
def build_schedule_by_categories_with_preferences(sorted_places, schedule_categories, preferred_tag_mapping, start_time):
    schedule = []
    used_place_ids = set()

    time_slots = [
        (start_time + timedelta(hours=i)).strftime("%H:%M") for i in range(len(schedule_categories))
    ]

    for i, category in enumerate(schedule_categories):
        subcategory_tags = preferred_tag_mapping.get(category, [])

        print(f"\n[DEBUG] 현재 카테고리: {category}")
        print(f"[DEBUG] 선호 태그: {subcategory_tags}")

        matched_place = None

        # 선호 태그로 먼저 찾기
        for place in sorted_places:
            if place.metadata.get("place_id") in used_place_ids:
                continue
            if any(tag in place.metadata.get("category", "") for tag in subcategory_tags):
                matched_place = place
                break

        # 못 찾으면 기본 카테고리에서 찾기
        if not matched_place:
            for place in sorted_places:
                if place.metadata.get("place_id") in used_place_ids:
                    continue
                if place.metadata.get("category", "") in subcategory_tags:
                    matched_place = place
                    break

        if matched_place:
            metadata = matched_place.metadata
            schedule.append({
                "time": time_slots[i],
                "desc": category,
                "name": metadata.get("name"),
                "category": metadata.get("category"),
                "address": metadata.get("address"),
                "distance_km": f"{metadata.get('distance', 0):.2f}km",
                "rating": metadata.get("rating"),
                "website": metadata.get("website"),
            })
            used_place_ids.add(metadata.get("place_id"))

    return schedule

@sync_to_async
def search_places_by_preferred_tags(user_query, preferred_tag_mapping):
    from .openai_chroma_config import place_vector_store
    all_docs = []
    seen_place_ids = set()

    for category, tags in preferred_tag_mapping.items():
        for tag in tags:
            results = place_vector_store.similarity_search(
                query=f"{user_query} {tag}",
                k=5,
                filter={"type": "place"}
            )
            for doc in results:
                place_id = doc.metadata.get("place_id")
                if place_id not in seen_place_ids:
                    all_docs.append(doc)
                    seen_place_ids.add(place_id)

    return all_docs

@sync_to_async
def classify_question_with_llm(user_query):
    chain = LLMChain(llm=llm, prompt=query_prompt)
    result = chain.invoke({"question": user_query})

    category = result.get("text", "").strip().lower()

    if category not in ["function", "place", "unknown"]:
        return "error"
    
    return category

#html로 변환 
@sync_to_async
def format_place_results_to_html(place_results, top_k=3):
    
    top_k = min(top_k, len(place_results))
    
    html_blocks = []

    for doc, score in place_results[:top_k]:
        metadata = doc.metadata
        content = doc.page_content

        html = f"""
        <div class="schedule-item">
          ⏰ 추천 장소<br/>
          📍 <strong>{metadata.get('name', '장소명 없음')}</strong><br/>
          🏷️ 카테고리: {metadata.get('category', '카테고리 없음')}<br/>
          📫 주소: {metadata.get('address', '주소 없음')}<br/>
          ☎️ 전화번호: {metadata.get('phone', '전화번호 없음')}<br/>
          🕒 영업시간: {metadata.get('opening_hours', '영업시간 정보 없음')}<br/>
          📏 위도/경도: {metadata.get('latitude', '-')}, {metadata.get('longitude', '-')}<br/>
          ⭐ 평점: {metadata.get('rating', '없음')} ({metadata.get('review_count', 0)}명)<br/>
          🔗 <a href="{metadata.get('website', '#')}" target="_blank">웹사이트 바로가기</a><br/>
          <br/>
          📝 설명: {content}
        </div><br/>
        """
        html_blocks.append(html)

    return f"""
    <div class="bot-response">
      <br/><p>요청하신 장소에 대한 추천 결과입니다. 상세 정보를 확인해보세요! 😊</p>
      {''.join(html_blocks)}
    </div>
    """