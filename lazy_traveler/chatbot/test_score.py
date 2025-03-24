from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
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

# 3. Chroma DB 로드
chroma_db = Chroma(
    collection_name="combined_collection",
    embedding_function=embeddings,
    persist_directory=vector_dir
)

# 4. 전체 문서 개수 가져오기
print(f"전체 문서 개수: {chroma_db._collection.count()}")

# 4. 사용자 질문에 대해 벡터화 및 유사도 검색 수행
user_question = "관심사 말고 위치로만 추천 가능해?"

# 5. Chroma에서 similarity_search_with_score 메서드를 호출하여 유사한 문서 검색
results = chroma_db.similarity_search_with_relevance_scores(user_question, k=1)

# 6. 유사도 점수와 함께 결과 출력

for res, score in results:
    if score >= 0.1:
        print(f"* {res.metadata}")
    print(f"* [유사도점수 ={score}]")    
    # print(f"* [SIM={score:3f}] {res.page_content} [{res.metadata}]")
