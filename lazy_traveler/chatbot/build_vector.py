from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma  # ✅ 최신 방식으로 변경
from langchain_openai import OpenAIEmbeddings
import json
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# OpenAI API 키 확인
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("⚠️ OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요!")

# 1. embeddings 도구 설정
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 2. 벡터 DB 저장 디렉토리 설정
vector_dir = "vector"
os.makedirs(vector_dir, exist_ok=True)

# 3. Chroma DB 생성
chroma_db = Chroma(
    collection_name="places",
    embedding_function=embeddings,
    persist_directory=vector_dir
)

# 4. JSON 파일에서 데이터 추출 및 벡터화
json_folder = "json_folder"
json_files = [f for f in os.listdir(json_folder) if f.endswith(".json")]

all_texts = []
all_metadatas = []

for json_filename in json_files:
    with open(os.path.join(json_folder, json_filename), "r", encoding="utf-8") as file:
        places = json.load(file)

    for place in places:
        text_data = f"{place.get('name', 'Unknown')} {place.get('category', 'Unknown')} {place.get('address', 'Unknown')}"
        metadata = {
            "name": place.get('name', 'Unknown'),
            "category": place.get('category', 'Unknown'),
            "address": place.get('address', 'Unknown'),
            "rating": place.get('rating', 'N/A'),
            "review_count": place.get('review_count', 'N/A'),
            "opening_hours": ', '.join(place.get('opening_hours', [])) if isinstance(place.get('opening_hours', []), list) else str(place.get('opening_hours', 'N/A')),
            "phone": place.get('phone', 'N/A'),
            "website": place.get('website', 'N/A'),
            "place_id": place.get('place_id', 'N/A')
        }
        all_texts.append(text_data)
        all_metadatas.append(metadata)

if all_texts:
    chroma_db.add_texts(all_texts, metadatas=all_metadatas)
    print(f"✅ 총 {len(all_texts)} 개의 데이터 벡터 저장 완료!")

# ✅ .persist() 제거 (자동 저장됨)
print("✅ 벡터 DB 저장 완료!")

