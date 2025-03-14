from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
import openai
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# API key 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# 1. 벡터 스토어 저장 경로 지정
base_dir = os.path.dirname(os.path.abspath(__file__))
vector_store_path = os.path.join(base_dir, "vector_store")

# 2. 임베딩 모델 설정
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

# 3. 기존 벡터 스토어 불러오기
vectorstore = Chroma(persist_directory=vector_store_path, embedding_function=embeddings)

# 4. Retriever 설정 (검색 기능만 담당)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})  # 관련 문서 3개 검색

# 5. LLM (GPT 모델) 설정
model = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

# 6. parser
output_parser = StrOutputParser()

# 7. 프롬프트 템플릿 설정
prompt = PromptTemplate(
    template="너는 전문가야. 사용자의 질문을 참고하여 문서만을 기반으로 정확한 답변을 제공해.\n\n"
             "질문: {question}\n\n"
             "참고 문서:\n{context}\n\n"
             "답변:",
    input_variables=["question", "context"]
)

# 8. Runnable 체인 정의
chain = (
    {
        "context": retriever | RunnablePassthrough(),  # 검색된 문서를 그대로 넘겨줌
        "question": RunnablePassthrough()  # 사용자의 질문 그대로 전달
    }
    | prompt  # 프롬프트 적용
    | model  # GPT 모델에 전달하여 답변 생성
    | output_parser  # 문자열로 변환
)

# 8. 질문 정의
query = "나 지금 북촌한옥마을인데 갈만한 베이커리 카페 알려줘."

# 9. 정제된 답변을 result 에 담음
result = chain.invoke(query)

# 10. 답변 출력
print(f"\n🤖 AI 답변:\n{result}\n")