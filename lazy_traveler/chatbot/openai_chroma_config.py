from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from langchain_chroma import Chroma
import openai
import os
from dotenv import load_dotenv  


# .env 파일 로드
load_dotenv()

# API key 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

current_dir = os.getcwd()

function_vector_dir = os.path.join(current_dir, 'vector_function')
place_vector_dir = os.path.join(current_dir,'vector_place')


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

# LLM 설정
llm = ChatOpenAI(model="gpt-4o-mini")