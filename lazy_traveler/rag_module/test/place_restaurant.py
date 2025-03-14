import googlemaps
import time
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# .env에서 API 키 불러오기
google_api_key = os.getenv("GOOGLE_API_KEY")

# Google Maps 클라이언트 초기화
gmaps = googlemaps.Client(key=google_api_key)

# ✅ 종로구를 커버할 15곳의 위치 
locations = ["청운효자동","경복궁","북촌한옥마을","광화문","종로1가","종로2가","종로3가","인사동","창덕궁","창경궁","사직동","통인시장","세종문화회관","혜화동","삼청동"]

# ✅ 검색할 장소 유형과 대응되는 카테고리 딕셔너리
#❗️❗️ { restaurant } ❗️❗️
type_category_map = {
    "restaurant": ["한식", "중식", "일식", "양식", "베트남 음식", "태국 음식", "햄버거", "피자", "비건", "브런치"]
}

# 중복 필터링을 위한 place_id 저장 set
visited_places = set()

def search_places(location, lat, lng, type, category):
    '''
    특정 위치를 받아서 장소 유형을 기반으로 주변장소를 검색하는 함수
    '''
    try:
        print(f"\n'{location}'을/를 중심으로 검색 중...")
        
        # 장소들을 저장할 변수
        place_dict = []
        
        # next_page_token은 다음 페이지의 데이터를 요청할 수 있는 키 역할 (Google Places API에서 여러 페이지로 나누어 반환된 결과의 다음 페이지를 요청하기 위한 토큰)
        next_page_token = None
        total_places = 0

        while True:
            try:
                places = gmaps.places_nearby(
                    location=(lat, lng),
                    radius=1000,
                    type=type,
                    keyword=category, # 키워드(한식 등) 적용
                    language='ko',
                    page_token=next_page_token
                )
                # 💊
                print(repr("places 생성"))
            except googlemaps.exceptions.ApiError as e:
                print(f"API 요청 에러 발생: {e}")
                break
            except Exception as e:
                print(f"알 수 없는 에러 발생: {e}")
                break
            
            # 결과가 없으면 즉시 종료
            results = places.get('results', [])
            
            if not results:
                print(f"✅ {location} 주변에 '{category}' 카테고리에 해당하는 장소가 없습니다.")
                break
            
            # type 별 장소들의 딕셔너리 (place_id만 추출하여 해당 place의 세부정보를 검색한다.)
            for place in results:
                place_id = place.get('place_id')
                
                # 중복된 장소(place_id)는 저장하지 않음
                if place_id in visited_places:
                    continue
                
                # place_id 저장하기
                visited_places.add(place_id)
                
                # 해당 장소의 세부 정보 요청
                details = gmaps.place(place_id=place_id, language='ko')
                
                # 해당 장소 세부 정보 가져오기
                result = details.get('result', {})
                
                # 위도/경도 가져오기
                geometry = result.get('geometry', {}).get('location', {})
                lat = geometry.get('lat', '정보 없음')
                lng = geometry.get('lng', '정보 없음')
                
                # 딕셔너리 형태로 저장하기
                place_info = {
                    '이름': result.get('name', '정보 없음'),
                    '카테고리': category,
                    '주소': result.get('formatted_address', '정보 없음'),
                    '위도': lat,  
                    '경도': lng,  
                    '평점': result.get('rating', '정보 없음'),
                    '리뷰 개수': result.get('user_ratings_total', '0'),
                    '영업시간': result.get('opening_hours', {}).get('weekday_text', '정보 없음'),
                    '전화번호': result.get('formatted_phone_number', '정보 없음'),
                    '웹사이트': result.get('url', '정보 없음'),
                    'place_id': place_id
                }
                
                place_dict.append(place_info)
                total_places += 1
            
            # 다음 페이지 토큰 가져오기
            next_page_token = places.get('next_page_token')
            
            # 더 이상 페이지가 없거나 60개 이상의 장소를 가져왔으면 반복 종료 (더 이상 추가 장소 콜 보내지 않음)
            if not next_page_token or total_places >= 60:
                break
        
            # Google Maps API의 요청 빈도 제한을 초과하지 않도록 2초 동안 프로그램 실행을 멈추기 (보통 초당 1개의 요청 정도를 권장함)
            time.sleep(5) 
        
        return place_dict
    
    except Exception as e:
        return f"에러 발생: {str(e)}"
    

def main():
    print("\n📝 반경 내에서 특정 타입의 장소를 찾아 문서화하는 프로그램\n")
    
    # ❗️조정❗️ 파일 경로
    current_dir = os.getcwd()
    txt_folder = os.path.join(current_dir, "txt_folder")
    if not os.path.exists(txt_folder):
        os.makedirs(txt_folder)
    # 폴더가 없으면 생성하고, 있으면 그냥 넘어간다
    os.makedirs(txt_folder, exist_ok=True)
    
    # 각 위치 별로 type 별 장소를 탐색하기 위한 반복문
    for location in locations:
        # location 의 위도 경도 가져오기
        geocode_result = gmaps.geocode(location)
        
        if not geocode_result:
            print(f"{location}의 위치를 찾을 수 없습니다.")
            continue
        
        lat = geocode_result[0]['geometry']['location']['lat']
        lng = geocode_result[0]['geometry']['location']['lng']
        
        # 💊
        print()
        print(repr(f"📍 {location} (위도: {lat}, 경도: {lng}) 검색 시작.."))
        
        # location 내에서 모든 type 별 장소들을 검색해서 문서화하기 (최종적으로 하나의 카테고리 문서에는 모든 location의 해당 카테고리의 장소들이 쌓임.)
        for type, categories in type_category_map.items():
            # restaurant의 각 카테고리를 담은 리스트 순회
            for category in categories:

                print(f"\n🔍 {category} ({type}) 검색 중..")
                try:
                    # ⭐️ location의 1km 반경 내의 장소들을 검색하고, 각 장소들의 세부정보 추출하기 
                    results = search_places(location, lat, lng, type, category)
                except Exception as e:
                    return f"에러 발생: {str(e)}"
                
                # 검색 결과를 저장할 문자열
                output_text = ""
                
                if isinstance(results, list):
                    '''search_places() 함수의 반환값이 리스트(정상적인 검색 결과)인지, 문자열(에러 메시지)인지 확인하여 로직 수행'''
                    output_text += "=" * 80
                    output_text += f"\n✅ {location} 주변 {category} ({type}) 리스트:\n"
                    output_text += "=" * 80 + "\n"
                    
                    if not results:
                        # 결과가 없으면 종료
                        print(repr(f"🚨 {location} '{category}' 카테고리의 장소가 더 이상 없습니다. 검색을 종료합니다."))
                        break  # 종료조건
                    
                    for p in results:
                        # 종로구이며, 영업시간 정보가 있고, 리뷰 개수가 50 이상인 장소만 문서에 추가
                        #❗️조정❗️
                        if "종로구" in p['주소'] and p['영업시간'] != "정보 없음" and int(p['리뷰 개수'])>=50:
                            output_text += f"장소 이름: {p['이름']}\n"
                            output_text += f"🔖 카테고리: {p['카테고리']}\n"
                            output_text += f"📍 주소: {p['주소']}\n"
                            output_text += f"🌎 위도: {p['위도']}\n"
                            output_text += f"🌎 경도: {p['경도']}\n"
                            output_text += f"⭐ 평점: {p['평점']} (리뷰 개수: {p['리뷰 개수']})\n"
                            output_text += f"⏰ 영업시간: {p['영업시간']}\n"
                            output_text += f"📞 전화번호: {p['전화번호']}\n"
                            output_text += f"🌐 웹사이트: {p['웹사이트']}\n"
                            output_text += f"🆔 place_id: {p['place_id']}\n"
                            output_text += "-" * 80 + "\n"
                    
                    output_text += "#" * 80 + "\n"
                # 에러 메시지일 경우 에러 메시지 그대로 텍스트 파일에 저장
                else:
                    output_text = results
                    
                # ❗️조정❗️
                file_path = os.path.join(txt_folder, f"종로_{category}.txt")
                # 텍스트 파일로 저장 (파일이 있으면 추가, 없으면 새로 생성)
                with open(file_path, "a", encoding="utf-8") as file:
                    file.write(output_text)
                    print(repr(f"✅ 검색 결과가 {file_path} 파일에 저장되었습니다."))


if __name__ == "__main__":
    main()
