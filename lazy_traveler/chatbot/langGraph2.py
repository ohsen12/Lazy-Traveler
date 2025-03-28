from dotenv import load_dotenv
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI

# API 키 정보 로드
load_dotenv()

# 그래프 상태 정의하는 클래스
class MyState(TypedDict):
    # 메시지 정의(list type 이며 add_messages 함수를 사용하여 메시지를 추가)
    messages: Annotated[str, add_messages] #Annotated는 타힙 힌트 + 추가 정보

# LLM 정의
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 챗봇 함수 정의
def chatbot(state: MyState):
    # 메시지 호출 및 반환
    return {"messages": [llm.invoke(state["messages"])]}

# 그래프 생성
graph = StateGraph(MyState)

# 'chatbot' 노드 추가
graph.add_node("chatbot", chatbot)

# START에서 챗봇 노드로 엣지 추가
graph.add_edge(START, "chatbot")

# 챗봇 노드에서 END로 엣지 추가
graph.add_edge("chatbot", END)

# 그래프 컴파일
app = graph.compile()

def run_chatbot():
    while True:
        # 사용자 입력 받기
        user_input = input("You: ")

        # "exit" 입력 시 종료
        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        # 그래프 이벤트 스트리밍
        for event in app.stream({"messages": [("user", user_input)]}):
            # 이벤트 값 출력
            for value in event.values():
                print("Assistant:", value["messages"][-1].content)

# 챗봇 실행
run_chatbot()