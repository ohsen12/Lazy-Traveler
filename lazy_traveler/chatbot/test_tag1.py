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

# 벡터 검색기 설정
retriever = chroma_db.as_retriever(
    search_kwargs={
        "k": 5  # 유사한 문서들을 더 많이 검색
    }
)

# 유저의 질문을 기반으로 검색 수행 (일단 태그를 고려하지 않음)
docs = retriever.invoke("공원 추천해줘")

# 4. 태그 필터링 (유저의 관심사나 태그를 기준으로 필터링)
user_tags = ["비건", "베이커리", "중식"]  # 예시로 유저 태그를 넣음

filtered_docs = []
for doc in docs:
    # 태그 기반으로 문서 필터링 (만약 태그 필터링을 적용하고 싶으면)
    doc_tags = doc.metadata.get("category", [])
    if any(tag in doc_tags for tag in user_tags):  # 유저의 태그가 문서의 태그에 포함되어 있으면
        filtered_docs.append(doc)

# 결과 출력 (태그 필터링된 문서들만)
for doc in filtered_docs:
    print(doc.metadata, doc.page_content)

# 만약 필터링된 결과가 없다면, 전체 문서에서 첫 번째 것만 출력하도록 설정 가능
if not filtered_docs:
    print("태그 필터링 후 결과가 없습니다. 전체 문서 중 첫 번째 결과 출력:")
    print(docs[0].metadata, docs[0].page_content)
