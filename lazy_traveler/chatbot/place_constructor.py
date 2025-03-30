import re
from typing import List


def extract_place_info(response_text: str) -> List[dict]:
    """
    챗봇 응답에서 장소 이름과 웹사이트의 cid 값을 추출

    Args:
        chatbot_response (str): 챗봇의 응답 텍스트

    Returns:
        list: 장소 이름과 cid 값을 담은 딕셔너리 리스트
            각 딕셔너리는 {"name": 장소 이름, "cid": cid 값} 형태
    """
    places = []
    extracted_places = set()  # 중복 추출 방지

    # HTML 형식인 경우 BeautifulSoup으로 파싱
    if '<div' in response_text or '<strong>' in response_text:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response_text, 'html.parser')

            # 패턴 1: schedule-item 클래스 내의 장소명 추출
            for item in soup.find_all('div', class_='schedule-item'):
                # 📍 이모지 다음에 오는 <strong> 태그 찾기
                text_content = item.get_text()
                strong_tags = item.find_all('strong')

                # 장소명이 포함된 strong 태그 찾기 (보통 📍 이모지 근처)
                place_name = None
                for strong in strong_tags:
                    if '📍' in strong.previous_sibling if strong.previous_sibling else '':
                        place_name = strong.text.strip()
                        break

                # strong 태그에서 찾지 못한 경우 텍스트에서 직접 찾기
                if not place_name:
                    place_match = re.search(r'📍\s*([^\n]+)', text_content)
                    if place_match:
                        place_name = place_match.group(1).strip()
                        # HTML 태그 제거
                        place_name = re.sub(r'<[^>]+>', '', place_name)

                if place_name and place_name not in extracted_places:
                    # cid 찾기 (웹사이트 링크에서)
                    cid = None
                    link = item.find('a', href=re.compile(r'maps\.google\.com/\?cid='))
                    if link:
                        href = link.get('href', '')
                        cid_match = re.search(r'cid=(\d+)', href)
                        if cid_match:
                            cid = cid_match.group(1)
                            website = href

                    places.append({"name": place_name, "cid": cid, "website": website})
                    extracted_places.add(place_name)

        except ImportError:
            # BeautifulSoup이 없는 경우 정규식만으로 처리
            print("[WARNING] BeautifulSoup을 찾을 수 없습니다. 정규식만으로 처리합니다.")
            pass

    # 정규식 패턴으로 추출 (HTML 파싱이 실패하거나 HTML이 아닌 경우)

    # 패턴 1: 숫자 이모지 + 장소: **장소명** 형식 (1️⃣, 2️⃣, 3️⃣ 등)
    for i in range(1, 10):  # 최대 9개까지 검색
        place_name_match = re.search(rf'{i}️⃣.*?장소: \*\*([^*]+)\*\*', response_text, re.DOTALL)
        if place_name_match:
            place_name = place_name_match.group(1).strip()
            if place_name in extracted_places:
                continue

            cid = None
            cid_match = re.search(rf'{i}️⃣.*?웹사이트: \[.+?\]\(https:\/\/maps\.google\.com\/\?cid=(\d+)\)', 
                                response_text, re.DOTALL)
            if cid_match:
                cid = cid_match.group(1).strip()
            places.append({"name": place_name, "cid": cid})
            extracted_places.add(place_name)

    # 패턴 2: 📍 이모지 + <strong>장소명</strong> 형식
    strong_matches = re.finditer(r'📍\s*<strong>([^<]+)</strong>', response_text, re.DOTALL)
    for match in strong_matches:
        place_name = match.group(1).strip()
        if not place_name or place_name in extracted_places:
            continue

        start_pos = match.start()
        search_text = response_text[start_pos:start_pos + 500]
        cid = None
        website = ""
        
        cid_match = re.search(r'https://maps\.google\.com/\?cid=(\d+)', search_text)
        if cid_match:
            cid = cid_match.group(1)
            website = f"https://maps.google.com/?cid={cid}"
        else:
            # fallback: 링크가 있다면 그것만이라도 website로 저장
            url_match = re.search(r'https://maps\.google\.com/\?cid=\d+', search_text)
            if url_match:
                website = url_match.group()

        places.append({"name": place_name, "cid": cid, "website": website})
        extracted_places.add(place_name)

    # 패턴 3: 📍 이모지 + 장소명 형식 (HTML 태그 없음)
    emoji_matches = re.finditer(r'📍\s*([^\n<]+)', response_text, re.DOTALL)
    for match in emoji_matches:
        place_name = match.group(1).strip()
        if place_name in extracted_places:
            continue

        # cid 찾기
        start_pos = match.start()
        search_text = response_text[start_pos:start_pos + 500]
        cid = None
        website = ""
        cid_match = re.search(r'https:\/\/maps\.google\.com\/\?cid=(\d+)', search_text, re.DOTALL)
        if cid_match:
            cid = cid_match.group(1).strip()
            website = f"https://maps.google.com/?cid={cid}"
        places.append({"name": place_name, "cid": cid, "website": website or ""})
        extracted_places.add(place_name)

    # 패턴 4: 장소: 장소명 형식
    place_matches = re.finditer(r'장소:\s*([^\n]+)', response_text, re.DOTALL)
    for match in place_matches:
        place_name = match.group(1).strip()
        # 별표(**) 제거
        place_name = re.sub(r'\*\*([^*]+)\*\*', r'\1', place_name)
        if place_name in extracted_places:
            continue

        # cid 찾기
        start_pos = match.start()
        search_text = response_text[start_pos:start_pos + 500]
        cid = None
        website = ""
        cid_match = re.search(r'웹사이트:.*?https:\/\/maps\.google\.com\/\?cid=(\d+)', search_text, re.DOTALL)
        if cid_match:
            cid = cid_match.group(1).strip()
            website = f"https://maps.google.com/?cid={cid}"
        places.append({"name": place_name, "cid": cid, "website": website or ""})
        extracted_places.add(place_name)

    # 디버깅용 로그
    if places:
        print(f"[DEBUG] 추출된 장소 정보: {places}")
    else:
        print("[WARNING] 장소 정보를 추출하지 못했습니다.")
    
    places = [p for p in places if p["name"].strip()]

    return places

import googlemaps
import logging
import os
from dotenv import load_dotenv


logger = logging.getLogger(__name__)
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


def get_place_id_by_name(place_name, api_key):
    """
    Google Places API를 사용하여 장소를 검색하고, 검색 결과의 place_id가 해당 장소와 일치하는지 확인

    Args:
        place_name (str): 장소 이름
        api_key (str): Google Places API 키

    Returns:
        str: 장소 이름이 일치하면 해당 장소의 Google Place ID를 반환
        None: 장소 이름이 일치하지 않거나 API 호출에 실패한 경우 None을 반환
    """
    gmaps = googlemaps.Client(key=api_key)

    try:
        places_result = gmaps.places(query=place_name)

        if places_result and places_result['results']:
            first_result = places_result['results'][0]
            return first_result.get('place_id')
        else:
            logger.debug("[get_place_id_by_name] 검색 결과가 존재하지 않습니다.")
            return None

    except Exception as e:
        logger.error(f"API 호출 실패: {str(e)}")
        return None


#from .utils import map_google_types_to_korean


def get_place_details(place_id, api_key):
    """
    Google Places API를 사용하여 Place ID에 해당하는 장소의 상세 정보를 크롤링

    Args:
        place_id (str): Google Place ID
        api_key (str): Google Places API 키

    Returns:
        dict: 장소의 상세 정보가 담긴 JSON 데이터 (딕셔너리 형태)
            API 호출 실패 시 None을 반환
    """
    gmaps = googlemaps.Client(key=api_key)

    try:
        place_details = gmaps.place(place_id=place_id, language="ko", fields=[
            'name', 'formatted_address', 'rating', 'website', 'opening_hours', 'geometry', 'formatted_phone_number',
            'type', 'place_id'
        ])

        if place_details and place_details['status'] == 'OK':
            return place_details['result']
        else:
            logger.error(f"[get_place_details] Place Details 요청 실패: {place_details['status']}")
            return None

    except Exception as e:
        logger.error(f"[get_place_details] API 호출 실패: {str(e)}")
        return None


# def format_place_details(place_data):
#     """
#     장소 상세 정보를 Place 모델 필드명에 맞춰 가공

#     Args:
#         place_data (dict): Google Places API에서 가져온 장소 상세 정보.

#     Returns:
#         dict: Place 모델 필드명에 맞춰 가공된 장소 상세 정보 딕셔너리.
#     """
#     if not place_data:
#         logger.debug(f"[format_place_details] 정보가 존재하지 않습니다: {place_data}")
#         return {}

#     formatted_details = {
#         'name': place_data.get('name', None),
#         'tags': map_google_types_to_korean(place_data.get('types', [])),
#         'address': place_data.get('formatted_address', None),
#         'latitude': place_data.get('geometry', {}).get('location', {}).get('lat', None),
#         'longitude': place_data.get('geometry', {}).get('location', {}).get('lng', None),
#         'rating': place_data.get('rating', None),
#         'place_id': place_data.get('place_id', None),
#         'website': place_data.get('website', None),
#         'opening_hours': place_data.get('opening_hours', {}).get('weekday_text', []) if
#         place_data.get('opening_hours') else [],
#     }

#     return formatted_details


from django.shortcuts import get_object_or_404
from accounts.models import User


# def save_place_to_db(place_details):
#     """
#     장소 상세 정보를 Place 모델 객체로 저장

#     Args:
#         place_details (dict): Place 모델 필드명에 맞춰 가공된 장소 상세 정보 딕셔너리
#     """
#     if not place_details:
#         logger.debug("[save_place_to_db] 저장할 장소의 정보가 없습니다.")
#         return 

#     try:
#         # place = Place(**place_details)
#         place, created = Place.objects.get_or_create(
#             place_id=place_details["place_id"],  # 중복 체크 기준
#             defaults={  # 새로 만들 때만 이 값들로 insert
#                 "name": place_details["name"],
#                 "tags": place_details["tags"],
#                 "address": place_details["address"],
#                 "latitude": place_details["latitude"],
#                 "longitude": place_details["longitude"],
#                 "rating": place_details["rating"],
#                 "website": place_details["website"],
#                 "opening_hours": place_details["opening_hours"],
#             }
#         )

#         if created:
#             logger.info(f"[save_place_to_db] 장소 저장 성공: {place.name}")
#         else:
#             logger.debug(f"[save_place_to_db] 이미 존재하는 장소: {place.name}")

#         place.save()
#         # return place
#         # place.save()
#         # logger.info(f"장소 '{place.name}'이(가) 성공적으로 저장되었습니다.")
#     except Exception as e:
#         logger.error(f"[save_place_to_db] 장소 저장 실패: {str(e)}")
#         return None


# def save_place_to_user(user, place_details):
#     """
#     장소 상세 정보를 Place 모델 객체로 저장하고, User 모델의 selected_places 필드에 추가

#     Args:
#         user (User): User 모델 객체
#         place_details (dict): Place 모델 필드명에 맞춰 가공된 장소 상세 정보 딕셔너리
#     """
#     if not place_details:
#         logger.debug("저장할 장소 정보가 존재하지 않습니다.")
#         return

#     try:
#         place, created = Place.objects.get_or_create(place_id=place_details['place_id'],defaults=place_details)

#         user = get_object_or_404(User, id=user.id)

#         user.selected_places.add(place)
#         logger.info(f"장소가 사용자의 selected_places에 추가되었습니다: {place.name}, {user}")

#     except Exception as e:
#         logger.warning(f"장소 저장 및 사용자 연결 실패: {str(e)}")


def process_place_info(places_info, api_key):
    """
    챗봇 응답에서 추출한 장소 정보를 처리하고 데이터베이스에 저장

    Args:
        places_info (list): 장소 정보 리스트 (extract_place_info 함수의 반환값)
        api_key (str): Google Places API 키
    """
    for place in places_info:
        place_name = place['name']
        cid = place['cid']

        # if cid:
        place_id = get_place_id_by_name(place_name, api_key)

        try:
            if place_id:
                place_data = get_place_details(place_id, api_key)

                if place_data:
                    formatted_details = format_place_details(place_data)
                    save_place_to_db(formatted_details)
                else:
                    logger.warning(f"[process_place_info] 장소의 상세 정보를 불러오는데 실패했습니다: {place_name}")
            else:
                logger.warning(f"[process_place_info] <장소: {place_name}> 와(과) <CID: {cid}>가 일치하지 않거나, 또는 API 호출에 실패했습니다.")
        except Exception as e:
            logger.warning(f"디버깅 에러메시지: {str(e)}")
        # else:
        #     logger.warning(f"[process_place_info] 장소의 CID가 존재하지 않습니다: {place_name}")