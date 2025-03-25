from django.conf import settings
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import json
import os
from dotenv import load_dotenv
import django
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lazy_traveler.settings')

django.setup()

# .env 파일 로드
load_dotenv()

def build_vector_store():   
    try:
        # 1. embeddings 도구 설정
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        current_dir = os.getcwd()

        function_vector_dir = os.path.join(current_dir, 'chatbot', 'vector_function')
        place_vector_dir = os.path.join(current_dir, 'chatbot', 'vector_place')

        # 벡터 DB가 존재하는지 확인 후 생성
        if not os.path.exists(function_vector_dir) or not os.listdir(function_vector_dir):
            os.makedirs(function_vector_dir, exist_ok=True)
            function_vector_store = Chroma(
                collection_name="function_collection",
                embedding_function=embeddings,
                persist_directory=function_vector_dir
            )

        if not os.path.exists(place_vector_dir) or not os.listdir(place_vector_dir):
            os.makedirs(place_vector_dir, exist_ok=True)
            place_vector_store = Chroma(
                collection_name="place_collection",
                embedding_function=embeddings,
                persist_directory=place_vector_dir
            )

        # 4. 질문 응답 데이터 추출 및 벡터화 (function_collection용)
        qa_folder = "qa_folder"  # 질문 응답 데이터가 들어있는 폴더
        qa_files = [f for f in os.listdir(qa_folder) if f.endswith(".json")]

        all_questions = []
        all_metadatas_qa = []

        for qa_filename in qa_files:
            with open(os.path.join(qa_folder, qa_filename), "r", encoding="utf-8") as file:
                qa_data = json.load(file)

            for qa in qa_data.get("질문들", []):  # "질문들" 키 아래의 데이터 처리
                question = qa.get("question", "Unknown question")
                answer = qa.get("answer", "Unknown answer")

                # 질문과 답변을 하나의 텍스트로 결합하여 벡터화
                text_data = f"질문: {question} 답변: {answer}"

                # 메타데이터에 type: qa 추가
                metadata = {
                    "question": question,
                    "answer": answer,
                    "type": "qa"
                }

                all_questions.append(text_data)
                all_metadatas_qa.append(metadata)

        # 5. 장소 데이터 추출 및 벡터화 (place_collection용)
        place_folder = "place_folder"  # 장소 데이터가 들어있는 폴더
        place_files = [f for f in os.listdir(place_folder) if f.endswith(".json")]

        all_texts_places = []
        all_metadatas_places = []

        for place_filename in place_files:
            with open(os.path.join(place_folder, place_filename), "r", encoding="utf-8") as file:
                places = json.load(file)

            for place in places:
                text_data = f"{place.get('name', 'Unknown')} {place.get('category', 'Unknown')} {place.get('address', 'Unknown')}"

                metadata = {
                    "name": place.get('name', 'Unknown'),
                    "category": place.get('category', 'Unknown'),
                    "address": place.get('address', 'Unknown'),
                    "latitude": place.get('latitude', 0),
                    "longitude": place.get('longitude', 0),
                    "rating": place.get('rating', 'N/A'),
                    "review_count": place.get('review_count', 'N/A'),
                    "opening_hours": ', '.join(place.get('opening_hours', [])) if isinstance(place.get('opening_hours', []), list) else str(place.get('opening_hours', 'N/A')),
                    "phone": place.get('phone', 'N/A'),
                    "website": place.get('website', 'N/A'),
                    "place_id": place.get('place_id', 'N/A'),
                    "type": "place"
                }

                all_texts_places.append(text_data)
                all_metadatas_places.append(metadata)

        # 6. 기능 데이터 벡터 저장 (function_collection에)
        if all_questions:
            function_vector_store.add_texts(all_questions, metadatas=all_metadatas_qa)
            print(f"✅ 총 {len(all_questions)} 개의 기능(질문 응답) 데이터 벡터 저장 완료!")

        # 7. 장소 데이터 벡터 저장 (place_collection에)
        if all_texts_places:
            place_vector_store.add_texts(all_texts_places, metadatas=all_metadatas_places)
            print(f"✅ 총 {len(all_texts_places)} 개의 장소 데이터 벡터 저장 완료!")

        print("✅ 벡터 DB 저장 완료!")
    except Exception as e:
        print(f"에러 발생: {str(e)}")


if __name__ == "__main__":  
    build_vector_store()