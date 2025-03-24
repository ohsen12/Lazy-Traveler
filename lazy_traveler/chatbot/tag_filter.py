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
        "filter": {
            "category": {"$in": ["비건", "베이커리", "중식"]},

        },
        "k": 2
    }
)
# 질의 수행
docs = retriever.invoke("공원 추천해줘")

# 결과 출력
for doc in docs:
    print(doc.metadata, doc.page_content)

