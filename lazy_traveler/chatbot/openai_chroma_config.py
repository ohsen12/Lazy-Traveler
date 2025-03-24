from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from langchain_chroma import Chroma
import openai
import os
from dotenv import load_dotenv  
from django.conf import settings

# persist_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'vector')

# .env 파일 로드
load_dotenv()

# API key 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# settings.BASE_DIR의 경로가 올바르게 설정되어 있는지 확인
# persist_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'vector_2')
function_vector_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'vector_function')
place_vector_dir = os.path.join(settings.BASE_DIR, 'chatbot', 'vector_place')

# # 경로가 존재하는지 확인하고, 없으면 생성
# if not os.path.exists(persist_dir):os.makedirs(persist_dir)

# embeddings 도구 설정
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

function_vector_store = Chroma(
    collection_name="function_collection",
    embedding_function=embeddings,
    persist_directory=function_vector_dir
)

place_vector_store = Chroma(
    collection_name="place_collection",
    embedding_function=embeddings,
    persist_directory=place_vector_dir
)

# 벡터 검색기 설정
retriever = place_vector_store.as_retriever(search_kwargs={"k": 5})  # 최대 5개 문서 검색

# LLM 설정
llm = ChatOpenAI(model="gpt-4o-mini")