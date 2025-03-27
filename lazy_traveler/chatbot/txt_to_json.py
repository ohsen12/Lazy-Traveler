import os
import json
import re

def convert_txt_to_json_files(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if not filename.endswith(".txt"):
            continue
        
        filepath = os.path.join(input_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        places = []
        entries = content.split("--------------------------------------------------------------------------------")
        
        for entry in entries:
            data = {}
            for line in entry.strip().split("\n"):
                if "장소 이름:" in line:
                    data["name"] = line.split("장소 이름:")[-1].strip()
                elif "카테고리:" in line:
                    data["category"] = line.split("카테고리:")[-1].strip()
                elif "주소:" in line:
                    data["address"] = line.split("주소:")[-1].strip()
                elif "위도:" in line:
                    data["latitude"] = float(line.split("위도:")[-1].strip())
                elif "경도:" in line:
                    data["longitude"] = float(line.split("경도:")[-1].strip())
                elif "평점:" in line:
                    match = re.search(r"평점: ([0-9.]+)", line)
                    if match:
                        data["rating"] = float(match.group(1))
                elif "리뷰 개수:" in line:
                    match = re.search(r"리뷰 개수: (\d+)", line)
                    if match:
                        data["review_count"] = int(match.group(1))
                elif "영업시간:" in line:
                    hours = line.split("영업시간:")[-1].strip()
                    data["opening_hours"] = eval(hours) if hours.startswith("[") else hours
                elif "전화번호:" in line:
                    data["phone"] = line.split("전화번호:")[-1].strip()
                elif "웹사이트:" in line:
                    data["website"] = line.split("웹사이트:")[-1].strip()
                elif "place_id:" in line:
                    data["place_id"] = line.split("place_id:")[-1].strip()

            if data.get("place_id"):
                places.append(data)

        # 중복 제거 (place_id 기준)
        unique_places = {place['place_id']: place for place in places}.values()

        output_filename = filename.replace(".txt", ".json")
        with open(os.path.join(output_dir, output_filename), "w", encoding="utf-8") as f:
            json.dump(list(unique_places), f, ensure_ascii=False, indent=2)

    print("변환 완료!=")

convert_txt_to_json_files("place_txt", "place_folder")