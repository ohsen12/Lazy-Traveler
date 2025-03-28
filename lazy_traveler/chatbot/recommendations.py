import logging
from typing import List, Tuple, Dict, Set
from functools import lru_cache

from django.core.cache import cache
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from accounts.models import User, Place
from .models import ChatHistory

logger = logging.getLogger(__name__)

# 1. 예외 처리 유틸리티 함수
def handle_exception(
    func_name: str, 
    exception: Exception, 
    custom_message: str = None, 
    log_level: str = "warning"
) -> Dict[str, object]:
    """
    일관된 예외 처리 및 로깅 함수.

    Args:
        func_name: 오류 발생 함수명.
        exception: 발생한 예외 객체.
        custom_message: 사용자 정의 메시지.
        log_level: 로깅 레벨.

    Returns:
        표준화된 에러 응답 딕셔너리.
    """
    error_message: str = custom_message or str(exception)
    log_method = getattr(logger, log_level, logger.warning)
    log_method(f"{func_name} 오류: {error_message}")
    
    return {
        "success": False,
        "message": error_message,
        "count": 0
    }

# 2. 캐시 활용 태그 유사성 함수 (함수 이름: get_user_tags_by_id)
@lru_cache(maxsize=100)
def get_user_tags_by_id(user_id: int) -> Set[str]:
    """
    사용자 태그를 효율적으로 가져오는 함수.

    Args:
        user_id: 조회할 사용자 ID (양의 정수).

    Returns:
        사용자 태그 집합 (예: {"맛집", "카페"}).
    """
    if not isinstance(user_id, int) or user_id <= 0:
        logger.warning("유효하지 않은 user_id 입력: {}".format(user_id))
        return set()
    
    try:
        user = get_object_or_404(User, id=user_id)
        # User 모델에서 tags는 ArrayField이므로 그대로 사용
        return set(tag.strip() for tag in user.tags) if user.tags else set()
    except Exception as e:
        handle_exception("get_user_tags_by_id", e)
        return set()

# 3. 정교한 사용자 유사성 측정
def get_similar_users(
    user_id: int, 
    threshold: float = 0.5, 
    top_n: int = 5
) -> List[int]:
    """
    사용자 태그 유사성을 정교하게 측정.

    Args:
        user_id: 기준 사용자 ID (양의 정수).
        threshold: 유사성 최소 임계값 (0-1 사이).
        top_n: 최대 반환할 유사 사용자 수.

    Returns:
        유사한 사용자 ID 리스트.
    """
    if not isinstance(user_id, int) or user_id <= 0:
        logger.warning("유효하지 않은 user_id 입력: {}".format(user_id))
        return []
    
    try:
        user_tags = get_user_tags_by_id(user_id)
        if not user_tags:
            return []

        user_similarities: List[Tuple[int, float]] = []
        for other_user in User.objects.exclude(id=user_id):
            other_tags = set(tag.strip() for tag in other_user.tags) if other_user.tags else set()
            
            # 자카드 유사도 계산
            intersection = len(user_tags.intersection(other_tags))
            union = len(user_tags.union(other_tags))
            similarity = intersection / union if union > 0 else 0
            
            if similarity >= threshold:
                user_similarities.append((other_user.id, similarity))

        sorted_users = sorted(user_similarities, key=lambda x: x[1], reverse=True)[:top_n]
        return [u_id for (u_id, _) in sorted_users]

    except Exception as e:
        handle_exception("get_similar_users", e, custom_message="유사 사용자 탐색 실패")
        return []

# 4. 개선된 채팅 히스토리 장소 추출
def extract_places_from_chathistory(
    user_id: int, 
    min_frequency: int = 1
) -> List[Tuple[str, int]]:
    """
    채팅 히스토리에서 장소 언급 빈도를 추출하는 함수.
    (추후 자연어 처리(NLP)를 적용하여 더 정교한 추출이 가능하도록 개선할 수 있음.)

    Args:
        user_id: 사용자 ID (양의 정수).
        min_frequency: 최소 언급 횟수.

    Returns:
        (장소명, 빈도) 튜플 리스트. 예: [("카페", 3), ("맛집", 2)]
    """
    if not isinstance(user_id, int) or user_id <= 0:
        logger.warning("유효하지 않은 user_id 입력: {}".format(user_id))
        return []
    
    try:
        user_chats = ChatHistory.objects.filter(user_id=user_id)
        
        from .place_constructor import extract_place_info
        
        # 챗봇 응답에서 추출한 장소 정보들을 저장할 리스트
        all_places = []
        
        # 각 채팅 히스토리에서 장소 정보 추출
        for chat in user_chats:
            # 챗봇 응답에서 장소 정보 추출
            extracted_places = extract_place_info(chat.response)
            all_places.extend(extracted_places)
        
        # 장소명과 출현 빈도를 저장할 딕셔너리
        place_counter: Dict[str, int] = {}
        
        # 추출된 장소들의 출현 빈도 계산
        for place_info in all_places:
            place_name = place_info.get('name')
            if place_name:
                place_counter[place_name] = place_counter.get(place_name, 0) + 1
        
        # 추가적으로 메시지 내용에서 직접 텍스트 매칭 (향후 NLP 기술 적용 가능)
        for chat in user_chats:
            text = f"{chat.message} {chat.response}".lower()
            
            # 이미 카운터에 있는 장소명들에 대해 추가 검색
            for place_name in place_counter.keys():
                if place_name.lower() in text:
                    place_counter[place_name] = place_counter.get(place_name, 0) + 1
        
        return [(place, count) for place, count in place_counter.items() if count >= min_frequency]

    except Exception as e:
        logger.warning(f"장소 추출 오류: {str(e)}")
        return []

# 5. 최종 추천 시스템
def get_chat_based_recommendations(
    user_id: int, 
    top_n: int = 5
) -> QuerySet:
    """
    종합적인 장소 추천 시스템.
    입력된 사용자 ID의 채팅 기록과 유사 사용자 분석을 통해 장소 추천을 진행함.

    Args:
        user_id: 추천 대상 사용자 ID (양의 정수).
        top_n: 최대 추천 장소 수.

    Returns:
        추천 장소 쿼리셋 (Django QuerySet).
    """
    if not isinstance(user_id, int) or user_id <= 0:
        logger.warning("유효하지 않은 user_id 입력: {}".format(user_id))
        return Place.objects.none()
    
    try:
        # 유사 사용자 찾기
        similar_user_ids = get_similar_users(user_id)
        if not similar_user_ids:
            print("유사 사용자 없음. 인기 장소 추천")
            return Place.objects.order_by('-rating')[:top_n]
        print(f"유사 사용자 찾음: {similar_user_ids}")

        combined_place_freq: Dict[str, int] = {}
        for sim_uid in similar_user_ids:
            sim_places = extract_places_from_chathistory(sim_uid)
            for place, freq in sim_places:
                combined_place_freq[place] = combined_place_freq.get(place, 0) + freq

        my_places = dict(extract_places_from_chathistory(user_id))
        
        
        weighted_places: Dict[str, int] = {}
        for place, total_freq in combined_place_freq.items():
            overlap_multiplier = 2 if place in my_places else 1
            weighted_places[place] = total_freq * overlap_multiplier

        top_place_names = sorted(weighted_places, key=weighted_places.get, reverse=True)[:top_n]
        return top_place_names

    except Exception as e:
        print(f"추천 시스템 오류: {str(e)}")
        return None