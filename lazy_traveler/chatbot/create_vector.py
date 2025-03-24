from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
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
vector_dir = "vector_2"
os.makedirs(vector_dir, exist_ok=True)

# 3. Chroma DB 생성
chroma_db = Chroma(
    collection_name="combined_collection",
    embedding_function=embeddings,
    persist_directory=vector_dir
)

# 4. 질문 응답 데이터 추출 및 벡터화
qa_folder = "qa_folder"  # 질문 응답 데이터가 들어있는 폴더
qa_files = [f for f in os.listdir(qa_folder) if f.endswith(".json")]

all_questions = []
all_answers = []
all_metadatas_qa = []

# JSON 파일에서 질문 응답 데이터 추출
for qa_filename in qa_files:
    with open(os.path.join(qa_folder, qa_filename), "r", encoding="utf-8") as file:
        qa_data = json.load(file)

    # '질문들' 키로 데이터를 가져오기
    for qa in qa_data.get("질문들", []):  # "질문들" 키 아래의 데이터 처리
        question = qa.get("question", "Unknown question")
        answer = qa.get("answer", "Unknown answer")
        
        # 질문과 답변을 하나의 텍스트로 결합하여 벡터화
        text_data = f"질문: {question} 답변: {answer}"
        
        # 메타데이터에 질문과 답변 저장
        metadata = {
            "question": question,
            "answer": answer
        }

        all_questions.append(text_data)
        all_answers.append(answer)
        all_metadatas_qa.append(metadata)

# 5. 장소 데이터 추출 및 벡터화
json_folder = "json_folder"  # 장소 데이터가 들어있는 폴더
json_files = [f for f in os.listdir(json_folder) if f.endswith(".json")]

all_texts_places = []
all_metadatas_places = []

for json_filename in json_files:
    with open(os.path.join(json_folder, json_filename), "r", encoding="utf-8") as file:
        places = json.load(file)

    for place in places:
        text_data = f"{place.get('name', 'Unknown')} {place.get('category', 'Unknown')} {place.get('address', 'Unknown')}"
        metadata = {
            "name": place.get('name', 'Unknown'),
            "category": place.get('category', 'Unknown'),
            "address": place.get('address', 'Unknown'),
            "latitude": place.get('latitude', 0),  # 위도 추가
            "longitude": place.get('longitude', 0),  # 경도 추가
            "rating": place.get('rating', 'N/A'),
            "review_count": place.get('review_count', 'N/A'),
            "opening_hours": ', '.join(place.get('opening_hours', [])) if isinstance(place.get('opening_hours', []), list) else str(place.get('opening_hours', 'N/A')),
            "phone": place.get('phone', 'N/A'),
            "website": place.get('website', 'N/A'),
            "place_id": place.get('place_id', 'N/A')
        }
        all_texts_places.append(text_data)
        all_metadatas_places.append(metadata)

# 6. 벡터화 및 저장
if all_questions:
    chroma_db.add_texts(all_questions, metadatas=all_metadatas_qa)
    print(f"✅ 총 {len(all_questions)} 개의 질문 응답 데이터 벡터 저장 완료!")

if all_texts_places:
    chroma_db.add_texts(all_texts_places, metadatas=all_metadatas_places)
    print(f"✅ 총 {len(all_texts_places)} 개의 장소 데이터 벡터 저장 완료!")

# 벡터 DB 저장 완료
print("✅ 벡터 DB 저장 완료!")
