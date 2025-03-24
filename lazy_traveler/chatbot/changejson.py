import json
import re
import os

# TXT 폴더 및 JSON 폴더 경로 설정
txt_folder = "txt_folder"
json_folder = "json_folder"
os.makedirs(json_folder, exist_ok=True)  # JSON 폴더가 없으면 생성

# TXT 폴더 내 모든 .txt 파일 탐지
txt_files = [f for f in os.listdir(txt_folder) if f.endswith(".txt")]

# 총 장소 수 카운트 변수
total_places_count = 0

# 각 TXT 파일에 대해 변환 처리
for txt_filename in txt_files:
    txt_path = os.path.join(txt_folder, txt_filename)

    # TXT 파일 읽기
    with open(txt_path, "r", encoding="utf-8") as file:
        data = file.read()

    # 패턴 정의 (각 장소 정보 추출)
    pattern = r"장소 이름: (.*?)\n🔖 카테고리: (.*?)\n📍 주소: (.*?)\n🌎 위도: ([\d.]+)\n🌎 경도: ([\d.]+)\n⭐ 평점: ([\d.]+) \(리뷰 개수: (\d+)\)\n⏰ 영업시간: (.*?)\n📞 전화번호: (.*?)\n🌐 웹사이트: (.*?)\n🆔 place_id: (.*?)\n"

    matches = re.findall(pattern, data, re.DOTALL)

    # JSON 데이터 변환
    places = []
    for match in matches:
        place = {
            "name": match[0],
            "category": match[1],
            "address": match[2],
            "latitude": float(match[3]),
            "longitude": float(match[4]),
            "rating": float(match[5]),
            "review_count": int(match[6]),
            "opening_hours": eval(match[7]),  # 문자열을 리스트로 변환
            "phone": match[8] if match[8] != "N/A" else None,
            "website": match[9] if match[9] != "N/A" else None,
            "place_id": match[10],
        }
        places.append(place)

    # JSON 파일 저장 경로 설정 (TXT 파일 이름 유지)
    json_filename = os.path.splitext(txt_filename)[0] + ".json"
    json_path = os.path.join(json_folder, json_filename)

    # JSON 파일 저장
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(places, json_file, ensure_ascii=False, indent=4)

    print(f"JSON 파일이 {json_path} 에 성공적으로 저장되었습니다.")

    # 총 장소 수 카운트
    total_places_count += len(places)

# 총 장소 수 출력
print(f"\n총 {total_places_count} 개의 장소가 처리되었습니다.")
