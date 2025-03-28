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
):
    """
    종합적인 장소 추천 시스템.
    입력된 사용자 ID의 채팅 기록과 유사 사용자 분석을 통해 장소 추천을 진행함.

    Args:
        user_id: 추천 대상 사용자 ID (양의 정수).
        top_n: 최대 추천 장소 수.

    Returns:
        추천 장소 이름 리스트.
    """
    if not isinstance(user_id, int) or user_id <= 0:
        logger.warning("유효하지 않은 user_id 입력: {}".format(user_id))
        return []
    
    try:
        print(f"[DEBUG] 추천 시작 - 사용자 ID: {user_id}")
        
        # 유사 사용자 찾기
        similar_user_ids = get_similar_users(user_id)
        print(f"[DEBUG] 유사 사용자 IDs: {similar_user_ids}")
        
        # 유사 사용자가 없는 경우 빈 리스트 반환
        if not similar_user_ids:
            print("[DEBUG] 유사 사용자 없음. 빈 결과 반환")
            return []
            
        # 유사 사용자들의 채팅에서 언급된 장소 카운트
        combined_place_freq: Dict[str, int] = {}
        
        # 모든 유사 사용자의 채팅 기록에서 장소 추출
        for sim_uid in similar_user_ids:
            sim_places = extract_places_from_chathistory(sim_uid)
            print(f"[DEBUG] 유사 사용자 {sim_uid}의 장소: {sim_places}")
            
            if not sim_places:
                print(f"[DEBUG] 유사 사용자 {sim_uid}에서 추출된 장소 없음")
                continue
                
            # 유사 사용자의 장소 빈도 합산
            for place, freq in sim_places:
                combined_place_freq[place] = combined_place_freq.get(place, 0) + freq
        
        print(f"[DEBUG] 유사 사용자들의 모든 장소 및 빈도: {combined_place_freq}")
        
        # 빈도 정보가 없으면 빈 리스트 반환
        if not combined_place_freq:
            print("[DEBUG] 유사 사용자들의 장소 정보 없음. 빈 결과 반환")
            return []
        
        # 내 장소 추출 (가중치 계산용)
        my_places = dict(extract_places_from_chathistory(user_id))
        print(f"[DEBUG] 내 장소: {my_places}")
        
        # 가중치 적용
        weighted_places: Dict[str, float] = {}
        for place, total_freq in combined_place_freq.items():
            # 내 장소와 겹치면 가중치 2배
            overlap_multiplier = 2.0 if place in my_places else 1.0
            weighted_places[place] = total_freq * overlap_multiplier
        
        print(f"[DEBUG] 가중치 적용된 장소 점수: {weighted_places}")
        
        # 점수 기준으로 정렬
        top_place_names = sorted(weighted_places.items(), key=lambda x: x[1], reverse=True)[:top_n]
        print(f"[DEBUG] 최종 추천 장소 및 점수: {top_place_names}")
        
        # 최종 추천 장소명만 추출하여 리스트로 반환
        result_places = [place_name for place_name, _ in top_place_names]
        print(f"[DEBUG] 최종 반환할 장소 이름 리스트: {result_places}")
        
        # 여기서 Place 객체를 찾는 대신, 추출된 장소 이름 리스트를 직접 반환
        return result_places
        
    except Exception as e:
        print(f"[DEBUG] 추천 시스템 전체 오류: {str(e)}")
        logger.error(f"추천 시스템 오류: {str(e)}")
        return []

def extract_places_from_response(response):
    """
    챗봇 응답에서 추천된 장소 이름을 추출하는 함수
    HTML 형식의 응답에서 schedule-item 클래스 내 장소명을 찾아 반환
    """
    from bs4 import BeautifulSoup
    import re
    
    # 응답이 문자열이 아니면 변환
    if not isinstance(response, str):
        if hasattr(response, 'response'):
            response = response.response
        else:
            return []
    
    # HTML 파싱
    soup = BeautifulSoup(response, 'html.parser')
    
    # 추천 장소 목록 저장할 리스트
    recommended_places = []
    
    # 각 schedule-item에서 장소명 추출
    for item in soup.find_all('div', class_='schedule-item'):
        # 방법 1: 📍 이모지 다음에 오는 텍스트 찾기
        text_content = item.get_text()
        match = re.search(r'📍\s*([^\n]+)', text_content)
        if match:
            place_name = match.group(1).strip()
            # <strong> 태그가 포함된 경우 제거
            place_name = re.sub(r'<[^>]+>', '', place_name)
            recommended_places.append(place_name)
            continue
        
        # 방법 2: 📍 이모지 다음에 오는 <strong> 태그 찾기
        pin_emoji = item.find(string=lambda text: '📍' in text if text else False)
        if pin_emoji and pin_emoji.find_next('strong'):
            place_name = pin_emoji.find_next('strong').text.strip()
            recommended_places.append(place_name)
            continue
    
    return recommended_places

def extract_places_from_chat_history(user_chats):
    """
    사용자의 채팅 히스토리에서 장소 이름을 추출하는 함수
    """
    all_places = []
    
    for chat in user_chats:
        # 챗봇 응답에서 장소 추출
        if hasattr(chat, 'response') and chat.response:
            places = extract_places_from_response(chat.response)
            all_places.extend(places)
    
    return all_places

def process_recommendations(user_id=None):
    """
    사용자의 채팅 히스토리를 분석하여 추천 장소를 처리하는 함수
    """
    from typing import Dict
    from .models import ChatHistory
    
    try:
        if user_id:
            user_chats = ChatHistory.objects.filter(user_id=user_id)
            # 챗히스토리에서 장소를 파싱하는 로직
            all_places = extract_places_from_chat_history(user_chats)
            
            place_counter: Dict[str, int] = {}
            
            # 장소별 등장 횟수 카운트
            for place in all_places:
                if place in place_counter:
                    place_counter[place] += 1
                else:
                    place_counter[place] = 1
            
            # 가장 많이 언급된 장소 순으로 정렬
            sorted_places = sorted(place_counter.items(), key=lambda x: x[1], reverse=True)
            
            # 상위 5개 장소 반환
            top_places = [place for place, count in sorted_places[:5]]
            
            return top_places
        
        return []
    except Exception as e:
        import logging
        logging.error(f"Error in process_recommendations: {str(e)}")
        return []