# OpenAI의 모델을 사용하기 위한 패키지
from langchain_openai import OpenAIEmbeddings
# ChromaDB를 LangChain과 연동하는 패키지 
from langchain.vectorstores import Chroma
# 커뮤니티에서 제공하는 다양한 기능을 포함하는 패키지
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.document_loaders import DirectoryLoader, TextLoader
# OpenAI API 키 로드
import openai
import os
from dotenv import load_dotenv


# .env 파일 로드
load_dotenv()

# API key 설정
openai.api_key = os.getenv("OPENAI_API_KEY")


def build_vector_store():
    '''
    벡터 DB 생성 함수: RAG를 구축하는 시점과 RAG를 사용하는 시점을 분리 (✅ LLM 사용 전 한 번만 실행하기)
    txt_folder 폴더 하의 모든 txt 파일을 로드하여 청킹과 임베딩 후 벡터 DB화 한다.
    '''
    try:
        # 현재 작업 디렉토리 출력
        current_dir = os.getcwd()
        print(f"현재 작업 디렉토리: {current_dir}")
        
        # 텍스트 파일 폴더 경로 확인
        txt_folder = os.path.join(current_dir, "txt_folder")
        print(f"텍스트 파일 폴더 경로: {txt_folder}")
        
        # 벡터 스토어 저장 경로 확인
        vector_store_path = os.path.join(current_dir, "vector_store")
        print(f"벡터 스토어 저장 경로: {vector_store_path}")
        
        # 1. 문서 불러오기 (txt_folder 하의 카테고리별 txt)
        loader = DirectoryLoader(txt_folder, glob="*.txt", loader_cls=TextLoader)
        docs = loader.load()
        print(f"로드된 문서 수: {len(docs)}")

        # 2. 문서 chunking 하기
        # chunk_size: 장소 하나 + 일부 추가 정보 포함 700, chunk_overlap: 청크 간에 중요한 정보가 끊어지지 않도록 오버랩 사이즈는 350으로 설정
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=350)
        splits = text_splitter.split_documents(docs)
        print(f"청크 수: {len(splits)}")

        # 3. embedding 도구 설정
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
            
        # 4. Chroma 벡터스토어 생성 및 저장
        vector_store = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=vector_store_path  # 벡터 스토어 저장 경로
        )
        
        # 저장 확인
        print(f"\n📂 벡터 스토어 문서 수: {vector_store._collection.count()}")
        print(f"📂 벡터스토어 저장 경로: {vector_store._persist_directory}")
        
    except Exception as e:
        print(f"에러 발생: {str(e)}")
        

# 해당 스크립트(.py 파일)가 직접 실행될 때만 build_vector_store() 함수를 실행
if __name__ == "__main__":
    '''
    이 파일이 독립적인 실행 파일로 실행될 때만 build_vector_store()를 실행하고,
    다른 모듈에서 import될 때는 실행되지 않는다.
    '''
    build_vector_store()