from typing import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
import chromadb
from dotenv import load_dotenv

# ✅ API 키 정보 로드
load_dotenv()

# ✅ 상태를 정의하는 TypedDict 클래스
class MyState(TypedDict):
    user_input: str  # 사용자의 질문
    response: str  # 챗봇의 응답

# ✅ OpenAI 모델 설정
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ✅ 질문 유형을 분석하는 함수
def classify_question(state: MyState) -> dict:
    question = state["user_input"]
    response = llm.invoke(f"다음 질문을 유형별로 분류하세요: {question}")

    # llm.invoke()는 Message 객체를 반환하므로 .content를 사용
    response_text = response.content if hasattr(response, 'content') else str(response)

    # 유형을 분석하여 적절한 노드로 연결
    if "FAQ" in response_text:
        next_node = "faq_response"
    elif "검색" in response_text:
        next_node = "fetch_from_db"
    else:
        next_node = "llm_response"

    return {"next": next_node}  # ✅ 반드시 딕셔너리 형태로 반환

# ✅ LLM을 활용한 답변 생성 함수
def generate_llm_response(state: MyState) -> MyState:
    question = state["user_input"]
    response = llm.invoke(f"사용자의 질문에 답해주세요: {question}")
    
    return {"user_input": question, "response": response.content, "next": END}

# ✅ ChromaDB 설정
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("faq_data")

# ✅ 벡터DB에서 검색하는 함수
def fetch_from_db(state: MyState) -> MyState:
    question = state["user_input"]
    
    # 벡터DB에서 관련 정보 검색
    results = collection.query(query_texts=[question], n_results=3)

    # 검색된 문서 리스트가 존재하는지 확인 후 반환
    response_text = results["documents"][0] if results["documents"] else "관련 정보를 찾을 수 없습니다."

    return {"user_input": question, "response": response_text, "next": END}

# ✅ 그래프 설정
workflow = StateGraph(MyState)

# ✅ 노드 추가
workflow.add_node("classify_question", classify_question)
workflow.add_node("faq_response", generate_llm_response)
workflow.add_node("llm_response", generate_llm_response)
workflow.add_node("fetch_from_db", fetch_from_db)

# ✅ 엣지 추가 (질문 유형에 따라 이동)
workflow.add_edge(START, "classify_question")
workflow.add_conditional_edges("classify_question", lambda state: state["next"])

# ✅ 종료 노드 설정
workflow.add_edge("faq_response", END)
workflow.add_edge("llm_response", END)
workflow.add_edge("fetch_from_db", END)

# ✅ 그래프 실행
app = workflow.compile()

# ✅ 예제 실행
response = app.invoke({"user_input": "뉴스 검색"})
print(response)
