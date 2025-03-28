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
    import re

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
        k=20,  # 검색 결과를 넉넉히 받아온 후 필터링
        filter={"type": "place"}
    )

def map_google_types_to_korean(types):
    mapping = {
    #자동차
    "car_dealer": "자동차 판매점",
    "car_rental": "렌터카",
    "car_repair": "자동차 수리점",
    "car_wash": "세차장",
    "electric_vehicle_charging_station": "전기차 충전소",
    "gas_station": "주유소",
    "parking": "주차장",
    "rest_stop": "휴게소",
    #비즈니스
    "corporate_office": "기업 사무실",
    "farm": "농장",
    "ranch": "목장",
    #문화
    "art_gallery": "전시장",
    "art_studio": "예술 작업실",
    "auditorium": "강당",
    "cultural_landmark": "문화 명소",
    "historical_place": "역사적인 장소",
    "monument": "기념물",
    "museum": "박물관",
    "performing_arts_theater": "공연 예술 극장",
    "sculpture": "조각상",
    #교육
    "library": "도서관",
    "preschool": "유치원",
    "primary_school": "초등학교",
    "school": "학교",
    "secondary_school": "중고등학교",
    "university": "대학교",
    #엔터테이먼트 및 여가
    "adventure_sports_center": "모험 스포츠 센터",
    "amphitheatre": "원형 극장",
    "amusement_center": "오락 센터",
    "amusement_park": "놀이공원",
    "aquarium": "수족관",
    "banquet_hall": "연회장",
    "barbecue_area": "바비큐 공간",
    "botanical_garden": "식물원",
    "bowling_alley": "볼링장",
    "casino": "카지노",
    "childrens_camp": "어린이 캠프",
    "comedy_club": "코미디 클럽",
    "community_center": "커뮤니티 센터",
    "concert_hall": "콘서트홀",
    "convention_center": "컨벤션 센터",
    "cultural_center": "문화 센터",
    "cycling_park": "자전거 공원",
    "dance_hall": "댄스홀",
    "dog_park": "반려견 공원",
    "event_venue": "이벤트 장소",
    "ferris_wheel": "대관람차",
    "garden": "정원",
    "hiking_area": "등산로",
    "historical_landmark": "역사적인 명소",
    "internet_cafe": "인터넷 카페",
    "karaoke": "노래방",
    "marina": "요트 정박장",
    "movie_rental": "영화 대여점",
    "movie_theater": "영화관",
    "national_park": "국립공원",
    "night_club": "나이트클럽",
    "observation_deck": "전망대",
    "off_roading_area": "오프로드 지역",
    "opera_house": "오페라 하우스",
    "park": "공원",
    "philharmonic_hall": "필하모닉 홀",
    "picnic_ground": "피크닉장",
    "planetarium": "천문관",
    "plaza": "광장",
    "roller_coaster": "롤러코스터",
    "skateboard_park": "스케이트보드 공원",
    "state_park": "주립공원",
    "tourist_attraction": "관광지",
    "video_arcade": "비디오 아케이드",
    "visitor_center": "관광 안내소",
    "water_park": "워터파크",
    "wedding_venue": "웨딩 장소",
    "wildlife_park": "야생동물 공원",
    "wildlife_refuge": "야생동물 보호구역",
    "zoo": "동물원",
    #시설
    "public_bath": "공중목욕탕",
    "public_bathroom": "공중화장실",
    "stable": "마구간",
    #금융
    "accounting": "회계 서비스",
    "atm": "ATM",
    "bank": "은행",
    #식음료
    "acai_shop": "아사이 전문점",
    "afghani_restaurant": "아프가니스탄 음식점",
    "african_restaurant": "아프리카 음식점",
    "american_restaurant": "미국 음식점",
    "asian_restaurant": "아시아 음식점",
    "bagel_shop": "베이글 가게",
    "bakery": "베이커리",
    "bar": "주점",
    "bar_and_grill": "바 앤 그릴",
    "barbecue_restaurant": "바비큐 음식점",
    "brazilian_restaurant": "브라질 음식점",
    "breakfast_restaurant": "아침식사 전문점",
    "brunch_restaurant": "브런치 음식점",
    "buffet_restaurant": "뷔페 음식점",
    "cafe": "카페",
    "cafeteria": "구내식당",
    "candy_store": "사탕 가게",
    "cat_cafe": "고양이 카페",
    "chinese_restaurant": "중식당",
    "chocolate_factory": "초콜릿 공장",
    "chocolate_shop": "초콜릿 가게",
    "coffee_shop": "커피숍",
    "confectionery": "제과점",
    "deli": "델리",
    "dessert_restaurant": "디저트 레스토랑",
    "dessert_shop": "디저트 가게",
    "diner": "다이너",
    "dog_cafe": "애견 카페",
    "donut_shop": "도넛 가게",
    "fast_food_restaurant": "패스트푸드점",
    "fine_dining_restaurant": "고급 레스토랑",
    "food_court": "푸드코트",
    "french_restaurant": "프랑스 음식점",
    "greek_restaurant": "그리스 음식점",
    "hamburger_restaurant": "햄버거 가게",
    "ice_cream_shop": "아이스크림 가게",
    "indian_restaurant": "인도 음식점",
    "indonesian_restaurant": "인도네시아 음식점",
    "italian_restaurant": "이탈리아 음식점",
    "japanese_restaurant": "일식당",
    "juice_shop": "주스 가게",
    "korean_restaurant": "한식당",
    "lebanese_restaurant": "레바논 음식점",
    "meal_delivery": "식사 배달",
    "meal_takeaway": "포장 음식",
    "mediterranean_restaurant": "지중해 음식점",
    "mexican_restaurant": "멕시코 음식점",
    "middle_eastern_restaurant": "중동 음식점",
    "pizza_restaurant": "피자 가게",
    "pub": "펍",
    "ramen_restaurant": "라멘집",
    "restaurant": "식당",
    "sandwich_shop": "샌드위치 가게",
    "seafood_restaurant": "해산물 음식점",
    "spanish_restaurant": "스페인 음식점",
    "steak_house": "스테이크하우스",
    "sushi_restaurant": "스시집",
    "tea_house": "찻집",
    "thai_restaurant": "태국 음식점",
    "turkish_restaurant": "터키 음식점",
    "vegan_restaurant": "비건 음식점",
    "vegetarian_restaurant": "채식 음식점",
    "vietnamese_restaurant": "베트남 음식점",
    "wine_bar": "와인 바",
    #지역
    "administrative_area_level_1": "광역 행정구역",
    "administrative_area_level_2": "기초 행정구역",
    "administrative_area_level_3": "행정구역 3단계",
    "administrative_area_level_4": "행정구역 4단계",
    "administrative_area_level_5": "행정구역 5단계",
    "administrative_area_level_6": "행정구역 6단계",
    "administrative_area_level_7": "행정구역 7단계",
    "locality": "지역",
    "sublocality": "하위 지역",
    "sublocality_level_1": "하위 지역 1단계",
    "sublocality_level_2": "하위 지역 2단계",
    "sublocality_level_3": "하위 지역 3단계",
    "sublocality_level_4": "하위 지역 4단계",
    "sublocality_level_5": "하위 지역 5단계",
    "country": "국가",
    "neighborhood": "이웃 지역",
    "postal_town": "우편 도시",
    "school_district": "학군",
    "colloquial_area": "구어적 지역명",
    "political": "정치적 구역",
    #지리/지형
    "archipelago": "군도",
    "continent": "대륙",
    "natural_feature": "자연 지형",
    "landmark": "랜드마크",
    #정부기관
    "city_hall": "시청",
    "courthouse": "법원",
    "embassy": "대사관",
    "fire_station": "소방서",
    "government_office": "정부 기관",
    "local_government_office": "지방 정부 기관",
    "neighborhood_police_station": "지역 파출소",
    "police": "경찰서",
    "post_office": "우체국",
    #우체국 관련
    "postal_code": "우편번호",
    "post_box": "우체통",
    "postal_code_prefix": "우편번호 접두사",
    "postal_code_suffix": "우편번호 접미사",
    "plus_code": "플러스 코드",
    #건강 및 웰니스
    "chiropractor": "척추지압사",
    "dental_clinic": "치과 클리닉",
    "dentist": "치과의사",
    "doctor": "의사",
    "drugstore": "약국",
    "hospital": "병원",
    "massage": "마사지",
    "medical_lab": "의료 실험실",
    "pharmacy": "약국",
    "physiotherapist": "물리치료사",
    "sauna": "사우나",
    "skin_care_clinic": "피부 클리닉",
    "spa": "스파",
    "tanning_studio": "태닝 스튜디오",
    "wellness_center": "웰니스 센터",
    "yoga_studio": "요가 스튜디오",
    #주택
    "apartment_building": "아파트 건물",
    "apartment_complex": "아파트 단지",
    "condominium_complex": "콘도 단지",
    "housing_complex": "주택 단지",
    #주소관련
    "premise": "구내",
    "subpremise": "구내 하위 단위",
    "floor": "층",
    "room": "방",
    "street_address": "도로명 주소",
    "street_number": "번지",
    "route": "경로",
    #숙박시설
    "bed_and_breakfast": "민박",
    "budget_japanese_inn": "저가 일본 여관",
    "campground": "캠핑장",
    "camping_cabin": "캠핑 캐빈",
    "cottage": "코티지",
    "extended_stay_hotel": "장기 숙박 호텔",
    "farmstay": "농가 체험 숙소",
    "guest_house": "게스트하우스",
    "hostel": "호스텔",
    "hotel": "호텔",
    "inn": "여관",
    "japanese_inn": "일본 여관",
    "lodging": "숙소",
    "mobile_home_park": "이동식 주택 공원",
    "motel": "모텔",
    "private_guest_room": "개인 게스트룸",
    "resort_hotel": "리조트 호텔",
    "rv_park": "RV 공원",
    #자연
    "beach": "해변",
    #예배장소
    "church": "교회",
    "hindu_temple": "힌두 사원",
    "mosque": "모스크",
    "synagogue": "유대교 회당",
    "place_of_worship": "예배 장소",
    #기타장소
    "point_of_interest": "관심 지점",
    "establishment": "시설",
    "geocode": "지리코드",
    "intersection": "교차로",
    "town_square": "광장",
    #서비스
    "astrologer": "점성술사",
    "barber_shop": "이발소",
    "beautician": "미용사",
    "beauty_salon": "미용실",
    "body_art_service": "바디아트 서비스",
    "catering_service": "케이터링 서비스",
    "cemetery": "묘지",
    "child_care_agency": "보육 기관",
    "consultant": "컨설턴트",
    "courier_service": "택배 서비스",
    "electrician": "전기 기술자",
    "florist": "꽃집",
    "food_delivery": "음식 배달",
    "foot_care": "발 관리",
    "funeral_home": "장례식장",
    "hair_care": "헤어 케어",
    "hair_salon": "헤어살롱",
    "insurance_agency": "보험 대리점",
    "laundry": "세탁소",
    "lawyer": "변호사",
    "locksmith": "자물쇠 수리공",
    "makeup_artist": "메이크업 아티스트",
    "moving_company": "이삿짐 센터",
    "nail_salon": "네일숍",
    "painter": "도장공",
    "plumber": "배관공",
    "psychic": "영매",
    "real_estate_agency": "부동산 중개업소",
    "roofing_contractor": "지붕 시공업자",
    "storage": "창고",
    "summer_camp_organizer": "여름캠프 주최자",
    "tailor": "재단사",
    "telecommunications_service_provider": "통신 서비스 제공업체",
    "tour_agency": "여행사",
    "tourist_information_center": "관광 안내소",
    "travel_agency": "여행사",
    "veterinary_care": "동물병원",
    #쇼핑
    "asian_grocery_store": "아시안 식료품점",
    "auto_parts_store": "자동차 부품점",
    "bicycle_store": "자전거 가게",
    "book_store": "서점",
    "butcher_shop": "정육점",
    "cell_phone_store": "휴대폰 매장",
    "clothing_store": "의류 매장",
    "convenience_store": "편의점",
    "department_store": "백화점",
    "discount_store": "할인점",
    "electronics_store": "전자 제품 매장",
    "food_store": "식료품점",
    "furniture_store": "가구점",
    "gift_shop": "기념품 가게",
    "grocery_store": "식료품점",
    "hardware_store": "철물점",
    "home_goods_store": "생활용품점",
    "home_improvement_store": "홈 인테리어 매장",
    "jewelry_store": "보석 가게",
    "liquor_store": "주류 판매점",
    "market": "시장",
    "pet_store": "애완동물 가게",
    "shoe_store": "신발 가게",
    "shopping_mall": "쇼핑몰",
    "sporting_goods_store": "스포츠 용품점",
    "store": "상점",
    "supermarket": "슈퍼마켓",
    "warehouse_store": "창고형 매장",
    "wholesaler": "도매상",
    #스포츠
    "arena": "경기장",
    "athletic_field": "운동장",
    "fishing_charter": "낚시 투어",
    "fishing_pond": "낚시터",
    "fitness_center": "피트니스 센터",
    "golf_course": "골프장",
    "gym": "헬스장",
    "ice_skating_rink": "아이스링크",
    "playground": "놀이터",
    "ski_resort": "스키 리조트",
    "sports_activity_location": "스포츠 활동 장소",
    "sports_club": "스포츠 클럽",
    "sports_coaching": "스포츠 코칭",
    "sports_complex": "종합 스포츠 센터",
    "stadium": "스타디움",
    "swimming_pool": "수영장",
    #교통
    "airport": "공항",
    "airstrip": "활주로",
    "bus_station": "버스 터미널",
    "bus_stop": "버스 정류장",
    "ferry_terminal": "페리 터미널",
    "heliport": "헬리포트",
    "international_airport": "국제공항",
    "light_rail_station": "경전철 역",
    "park_and_ride": "환승 주차장",
    "subway_station": "지하철역",
    "taxi_stand": "택시 승강장",
    "train_station": "기차역",
    "transit_depot": "교통 차량 기지",
    "transit_station": "환승역",
    "truck_stop": "화물차 휴게소",
    #기능적 태그
    "general_contractor": "종합건설업체",
    "finance": "금융",
    "food": "음식",
    "health": "건강",
    }

    
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

@sync_to_async
def get_preferred_tags_by_schedule(user_tags, schedule_categories):

    result = {}
    for category in schedule_categories:
        default_subcategories = CATEGORY_MAPPING.get(category, [])
        preferred = [tag for tag in default_subcategories if tag in user_tags]

        result[category] = preferred if preferred else default_subcategories

    return result

# 대화 내역을 가져오는 함수
@sync_to_async
def get_context(session_id, max_turns=5):
    chat_history = ChatHistory.objects.filter(session_id=session_id).order_by("-created_at")[:max_turns]
    return "\n\n".join([f"User: {chat.message}\nBot: {chat.response}" for chat in reversed(chat_history)])


   
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
- 운영시간: {place['opening_hours']} 
- 거리: {place['distance_km']}
- 평점: {place['rating']}
- 웹사이트: {place['website']}
        """)
    return "\n".join(lines)



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
