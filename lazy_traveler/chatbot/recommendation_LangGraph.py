from langgraph.graph import StateGraph, END, START
from datetime import datetime
from .prompt import place_prompt
from typing import TypedDict
from .utils import (
    get_user_tags,
    sort_places_by_distance,
    schedule_to_html,
    build_schedule_by_categories_with_preferences,
    determine_schedule_template,
    get_preferred_tags_by_schedule,
    classify_question_with_llm,
    format_place_results_to_html,
    filter_open_places_with_llm,
    search_places,
    fast_search_places_by_preferred_tags
)
from .openai_chroma_config import function_vector_store, llm

# ✅ 상태를 정의하는 TypedDict 클래스
class MyState(TypedDict):
    user_query: str
    response: str
    session_id: str | None
    username: str | None
    latitude: float
    longitude: float
    question_type: str  # 추가된 question_type 필드
    timestamp: datetime


# ✅ 1. 질문 분류 노드
async def classify_question(state: MyState) -> MyState:
    question_type = await classify_question_with_llm(state["user_query"])
    
    mapping = {
        "function": "handle_function_query",
        "place": "handle_place_query",
        "schedule": "handle_schedule_query",
        "unknown": "handle_unknown_query"
    }

    #####
    state["__condition__"] = mapping.get(question_type, "handle_unknown_query")

    state["question_type"] = question_type
    state["response"] = ""
    return state


# ✅ 2. 기능 질문 처리
async def handle_function_query(state: MyState) -> MyState:
    function_results = function_vector_store.similarity_search_with_score(
        query=state["user_query"],
        k=1,
        filter={"type": "qa"}
    )
    
    if function_results and function_results[0][1] <= 1.1:
        state["response"] = function_results[0][0].metadata.get("answer", "기능 관련 정보를 찾을 수 없습니다.")
    else:
        state["response"] = "기능 관련 정보를 찾을 수 없습니다."
    
    return state


# ✅ 3. 장소 검색 처리
async def handle_place_query(state: MyState) -> MyState:
    place_results = await search_places(state["user_query"], state["latitude"], state["longitude"])
    # state["response"] = await format_place_results_to_html(place_results)
    state["response"] = {
    "type": "place",
    "html": await format_place_results_to_html(place_results),
    "count": len(place_results)
    }
    return state


# ✅ 4. 일정 스케줄링 처리
async def handle_schedule_query(state: MyState) -> MyState:
    # datetime_input이 주어지지 않으면 현재 시간(now) 사용
    now = state["timestamp"] 
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    start_time = now

    schedule_type, schedule_categories = await determine_schedule_template(now)
    if schedule_type == "불가시간":
        state["response"] = "스케줄링 불가시간입니다. 오전 8시부터 오후 11시까지만 스케줄링이 가능합니다."
        return state


    user_tags = await get_user_tags(state["username"])
    preferred_tag_mapping = await get_preferred_tags_by_schedule(user_tags, schedule_categories)
    docs = await fast_search_places_by_preferred_tags(state["user_query"], preferred_tag_mapping)

    sorted_docs = await sort_places_by_distance(docs, state["latitude"], state["longitude"])
    filtered_docs = await filter_open_places_with_llm(sorted_docs, now)

    schedule = await build_schedule_by_categories_with_preferences(
        filtered_docs, schedule_categories, preferred_tag_mapping, start_time
    )

    schedule_text = await schedule_to_html(schedule)

    state["response"] = {
    "type": "schedule",
    "schedule_text": schedule_text,
    "time_context": current_time,
    "question": state["user_query"]
}

    return state


# ✅ 5. 알 수 없는 질문 처리
async def handle_unknown_query(state: MyState) -> MyState:
    state["response"] = "죄송합니다.😢 기능, 장소, 일정 스케줄링에 대해 문의해 주세요. 😊 예) '회원가입 하는 법', '스케줄링 해줘', '맛집 추천해줘'"
    return state

# 조건 분기 함수
def route_condition(state: dict) -> str:
    return state["__condition__"]

async def get_recommendation(
    user_query: str,
    session_id: str | None = None,
    username: str | None = None,
    latitude: float = 37.5704,
    longitude: float = 126.9831,
    timestamp: datetime | None = None) -> str: #####


    state: MyState = {
        "user_query": user_query,
        "response": "",
        "session_id": session_id,
        "username": username,
        "latitude": latitude if latitude is not None else 37.5704,
        "longitude": longitude if longitude is not None else 126.9831,
        "question_type": "",
        "timestamp": timestamp or datetime(2025, 4, 1, 12, 0, 0) ##### datetime.now()수정
    }

    # ✅ LangGraph 생성
    graph = StateGraph(MyState)

    # 📌 노드 추가
    graph.add_node("classify_question", classify_question)
    graph.add_node("handle_function_query", handle_function_query)
    graph.add_node("handle_place_query", handle_place_query)
    graph.add_node("handle_schedule_query", handle_schedule_query)
    graph.add_node("handle_unknown_query", handle_unknown_query)


# ✅ 분기 설정(condition_key 명시)
    graph.add_conditional_edges(
            "classify_question",
            path=route_condition,
            path_map={
                "handle_function_query": "handle_function_query",
                "handle_place_query": "handle_place_query",
                "handle_schedule_query": "handle_schedule_query",
                "handle_unknown_query": "handle_unknown_query"
            }
        )

    # ✅ 시작 및 종료 설정
    graph.add_edge(START, "classify_question")
    graph.add_edge("handle_function_query", END)
    graph.add_edge("handle_place_query", END)
    graph.add_edge("handle_schedule_query", END)
    graph.add_edge("handle_unknown_query", END)

    # ✅ 그래프 컴파일
    compiled_graph = graph.compile()

    # ✅ 그래프를 YAML 파일로 저장 (옵션)
    # compiled_graph.save("chatbot_graph.yaml")

    # ✅ 실행
    result = await compiled_graph.ainvoke(state)

    return {
    "user_query": result["user_query"],
    "response": result["response"],
    "question_type": result.get("question_type", "unknown")
}