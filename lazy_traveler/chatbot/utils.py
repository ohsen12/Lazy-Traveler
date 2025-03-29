import math
from .models import ChatHistory
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from .openai_chroma_config import place_vector_store, llm
from asgiref.sync import sync_to_async
from langchain.chains import LLMChain
from .prompt import query_prompt, opening_hours_prompt
from geopy.distance import geodesic  # 거리 계산 라이브러리

User = get_user_model()

#카테고리 대분류
CATEGORY_MAPPING = {
    "볼거리": ["공원", "관광명소", "전시","서점"],
    "맛집": ["베이커리", "베트남 음식", "브런치", "비건", "양식", "일식", "중식", "태국 음식", "피자", "한식", "햄버거"],
    "아침 식사": ["한식", "비건", "브런치"],
    "야식": ["주점", "피자", "햄버거", "중식"],
    "카페": ["카페", "브런치", "베이커리"]
}

#유저 질문 기능 분류(llm)
@sync_to_async
def classify_question_with_llm(user_query):
    chain = LLMChain(llm=llm, prompt=query_prompt)
    result = chain.invoke({"question": user_query})

    category = result.get("text", "").strip().lower()

    if category not in ["function", "place", "schedule","unknown"]:
        return "error"
    
    return category

#place 검색 및 거리 계산
@sync_to_async
def search_places(user_query, user_latitude, user_longitude):
    # 1️⃣ 기본 벡터 검색 실행
    place_results = place_vector_store.similarity_search_with_score(
        query=user_query,
        k=10,  # 검색 결과를 넉넉히 받아온 후 필터링
        filter={"type": "place"}
    )
    
    # 2️⃣ 거리 기반 필터링 및 정렬
    place_results_with_distance = []
    for doc, _ in place_results:
        place_metadata = doc.metadata
        place_lat = float(place_metadata.get("latitude"))
        place_lon = float(place_metadata.get("longitude"))

        if place_lat is not None and place_lon is not None:
            # 유클리드 거리 대신 실제 지구 거리(위경도) 계산
            place_distance = geodesic((user_latitude, user_longitude), (place_lat, place_lon)).km
            place_metadata["distance"] = place_distance
            place_results_with_distance.append((doc, place_distance))

    # 3️⃣ 거리 기반으로 정렬 (가까운 순서)
    sorted_places = sorted(place_results_with_distance, key=lambda x: x[1])  # 거리 기준 정렬
    return sorted_places[:3]  # 최종 상위 3개 선택

#place 결과 html로 변환 
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
          📏 거리: {metadata.get('distance', '거리 정보 없음'):.2f} km <br/>
          ⭐ 평점: {metadata.get('rating', '없음')} ({metadata.get('review_count', 0)}명)<br/>
          🔗 <a href="{metadata.get('website', '#')}" target="_blank">웹사이트 바로가기</a><br/>
          <br/>
          📝 설명: {content}
        </div>
        <hr/>
        """
        html_blocks.append(html)

    return f"""
    <div class="bot-response">
      <br/><p>요청하신 장소에 대한 추천 결과입니다. 상세 정보를 확인해보세요! 😊</p>
      {''.join(html_blocks)}
    </div>
    """

#시간 기반 스케줄링표 지정
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

#대분류 중 사용자가 태그만 선택
@sync_to_async
def get_preferred_tags_by_schedule(user_tags, schedule_categories):

    result = {}
    for category in schedule_categories:
        default_subcategories = CATEGORY_MAPPING.get(category, [])
        preferred = [tag for tag in default_subcategories if tag in user_tags]

        result[category] = preferred if preferred else default_subcategories

    return result

#태그 기반으로 장소 검색
@sync_to_async
def search_places_by_preferred_tags(user_query, preferred_tag_mapping):
    from .openai_chroma_config import place_vector_store
    all_docs = []
    seen_place_ids = set()

    for category, tags in preferred_tag_mapping.items():
        for tag in tags:
            results = place_vector_store.similarity_search(
                query=f"{user_query} {tag}",
                k=2,
                filter={"type": "place"}
            )
            for doc in results:
                place_id = doc.metadata.get("place_id")
                if place_id not in seen_place_ids:
                    all_docs.append(doc)
                    seen_place_ids.add(place_id)

    return all_docs

@sync_to_async
def fast_search_places_by_preferred_tags(user_query, preferred_tag_mapping):
    from .openai_chroma_config import place_vector_store

    all_docs = []
    seen_place_ids = set()

    for category, tags in preferred_tag_mapping.items():
        if not tags:
            continue

        query = f"{user_query} " + " ".join(tags)
        print(f"[DEBUG] {category}' 쿼리: {query}")

        results = place_vector_store.similarity_search(
            query=query,
            k=5,
            filter={"type": "place"}
        )

        for doc in results:
            place_id = doc.metadata.get("place_id")
            if place_id and place_id not in seen_place_ids:
                all_docs.append(doc)
                seen_place_ids.add(place_id)

    print(f"[DEBUG] 총 장소 결과 개수: {len(all_docs)}")
    return all_docs
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

    return sorted(
        places,
        key=lambda x: (
            x.metadata.get('distance', float('inf')) if hasattr(x, "metadata") else x.get('distance', float('inf'))
        )
    )

llm_chain = LLMChain(llm=llm, prompt=opening_hours_prompt)
#운영시간 확인
async def filter_open_places_with_llm(docs, now: datetime):

    results = []
    weekday_korean = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][now.weekday()]
    visit_time = now.strftime("%Y-%m-%d %H:%M")

    for doc in docs:
        metadata = doc.metadata
        opening_hours = metadata.get("opening_hours")

        if not opening_hours:
            continue

        try:
            response = await llm_chain.ainvoke({
                "opening_hours": opening_hours,
                "visit_time": visit_time,
                "weekday": weekday_korean
            })
            answer = response.get("text", "").strip()
            if "열려 있음" in answer:
                results.append(doc)
        except Exception as e:
            print(f"error: {e}")
            continue

    return results

#선호 태그와 일정 카테고리 기반 스케줄 생성
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
                "opening_hours": metadata.get("opening_hours"),
                "address": metadata.get("address"),
                "distance_km": f"{metadata.get('distance', 0):.2f}km",
                "rating": metadata.get("rating"),
                "website": metadata.get("website"),
            })
            used_place_ids.add(metadata.get("place_id"))

    return schedule

# 스케줄 데이터 텍스트 변환
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
- 운영시간: {place['opening_hours']} 
- 거리: {place['distance_km']}
- 평점: {place['rating']}
- 웹사이트: {place['website']}
        """)
    return "\n".join(lines)

@sync_to_async
def schedule_to_html(schedule: list[dict]) -> str:

    html_blocks = []

    for place in schedule:
        html = f"""
        <div class="schedule-item">
          ⏰ <strong>{place['time']}</strong> - {place['desc']}<br/>
          📍 <strong>{place['name']}</strong><br/>
          🏷️ 카테고리: {place.get('category', '없음')}<br/>
          📫 주소: {place.get('address', '없음')}<br/>
          🕒 운영시간: {place.get('opening_hours', '없음')}<br/>
          📏 거리: {place.get('distance_km', 'N/A')}<br/>
          ⭐ 평점: {place.get('rating', 'N/A')}<br/>
          🔗 <a href="{place.get('website', '#')}" target="_blank">웹사이트 바로가기</a>
        </div>
        <hr/>
        """
        html_blocks.append(html)

    return f"""
    <div class="bot-response">
      <p>📍 추천 일정을 아래에서 확인해보세요!</p>
      {''.join(html_blocks)}
    </div>
    """

# 대화 내역을 가져오는 함수
@sync_to_async
def get_context(session_id, max_turns=5):
    chat_history = ChatHistory.objects.filter(session_id=session_id).order_by("-created_at")[:max_turns]
    return "\n\n".join([f"User: {chat.message}\nBot: {chat.response}" for chat in reversed(chat_history)])
