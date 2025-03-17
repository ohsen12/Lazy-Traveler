import os
import math
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
import openai
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# API key 설정
openai.api_key = os.getenv("OPENAI_API_KEY")


def build_vector_store():
    try:
        current_dir = os.getcwd()
        print(f"현재 작업 디렉토리: {current_dir}")
        
        chatbot_dir = os.path.join(current_dir, "chatbot")  # chatbot 디렉토리 경로
        
        txt_folder = os.path.join(chatbot_dir, "txt_folder")  # chatbot/txt_folder 경로
        print(f"텍스트 파일 폴더 경로: {txt_folder}")

        # 폴더 존재 여부 확인
        if not os.path.exists(txt_folder):
            print(f"❌ 경로 오류: {txt_folder} 폴더가 존재하지 않습니다.")
        else:
            print(f"✅ 텍스트 폴더 경로: {txt_folder}")

        
        # 벡터 스토어 저장 경로 확인
        vector_store_path = os.path.join(current_dir, "vector_store")
        print(f"벡터 스토어 저장 경로: {vector_store_path}")
        
        # 1. 폴더 내 모든 텍스트 파일 읽기
        all_docs = []
        for filename in os.listdir(txt_folder):
            if filename.endswith(".txt"):
                txt_file_path = os.path.join(txt_folder, filename)
                try:
                    with open(txt_file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                        print(f"파일 로딩 성공: {filename}")
                        print(f"파일 내용의 첫 100자: {content[:100]}")
                        
                        # 2. 문서 chunking 하기
                        text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=350)
                        splits = text_splitter.split_text(content)
                        print(f"청크 수: {len(splits)}")

                        # 3. 문자열을 Document 객체로 변환
                        docs = [Document(page_content=split) for split in splits]
                        all_docs.extend(docs)
                        
                except Exception as e:
                    print(f"파일 로딩 중 오류 발생: {e}")
                    continue

        print(f"총 {len(all_docs)} 개의 Document 객체 수집 완료.")

        # 4. embedding 도구 설정
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        
        # 5. Chroma 벡터스토어 초기화
        vector_store = Chroma(persist_directory=vector_store_path, embedding_function=embeddings)

        # 6. 배치 크기 조정 및 벡터 처리
        batch_size = 166  # 최대 배치 크기
        num_batches = math.ceil(len(all_docs) / batch_size)  # 총 배치 수 계산

        for i in range(num_batches):
            batch_start = i * batch_size
            batch_end = min((i + 1) * batch_size, len(all_docs))
            batch = all_docs[batch_start:batch_end]
            
            # 배치에 대해 임베딩 처리
            print(f"배치 {i+1}/{num_batches} 처리 중, 문서 수: {len(batch)}")
            vectors = embeddings.embed_documents([doc.page_content for doc in batch])

            # 벡터와 문서 데이터를 Chroma에 추가
            # 배치의 메타데이터 추가: 파일명, 청크 번호
            vector_store.add_texts([doc.page_content for doc in batch],
                                   metadatas=[{"filename": txt_file_path, "chunk_id": idx} for idx in range(len(batch))])

            # 디버깅을 위한 배치별 상태 출력
            print(f"배치 {i+1}/{num_batches} 완료")

        # 저장 확인
        print(f"\n📂 벡터 스토어 문서 수: {vector_store._collection.count()}")
        print(f"📂 벡터스토어 저장 경로: {vector_store._persist_directory}")
        
    except Exception as e:
        print(f"에러 발생: {str(e)}")


if __name__ == "__main__":  
    build_vector_store()
