from datetime import datetime
from langchain.chains import LLMChain
from .prompt import function_prompt, place_prompt, query_prompt
from .utils import get_context, get_user_tags, sort_places_by_distance, schedule_to_text, build_schedule_by_categories, map_tags_to_categories, determine_schedule_template, classify_question_with_vector
from .openai_chroma_config import function_vector_store, retriever, llm


async def get_recommendation(user_query, session_id=None, username=None, latitude=None, longitude=None):
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    start_time = now

    if latitude is None or longitude is None:
        latitude, longitude = 37.5704, 126.9831

    question_type = await classify_question_with_vector(user_query)

    if question_type == "function":
        # 기능 벡터DB에서 검색된 문서 가져오기
        function_docs = await function_vector_store.similarity_search(user_query, k=3)

        # 벡터 검색 결과가 없을 경우 예외처리
        if not function_docs:
            return "기능 관련 정보를 찾을 수 없습니다."

        # 문서 내용을 context로 준비
        function_context = "\n".join([doc.page_content for doc in function_docs])
        if not function_context.strip():
            return "기능 관련 정보를 찾을 수 없습니다."

        # 기능용 프롬프트 + LLM 체인 호출
        chain = function_prompt | llm

        result = await chain.ainvoke({
            "context": function_context,
            "question": user_query
        })

        return result.content.strip() if result.content else "기능 관련 답변을 제공할 수 없습니다."

    # 태그 가져오기
    user_tags = await get_user_tags(username)
    user_categories = await map_tags_to_categories(user_tags)

    schedule_type, schedule_categories = await determine_schedule_template(now)
    if schedule_type == "불가시간":
        return "스케줄링 불가시간입니다."
    

    # 질문 정제 LLMChain 생성
    query_transform_chain = LLMChain(
    llm=llm,
    prompt=query_prompt
    )
    # wlfans wjdwp
    transformed_query_result = await query_transform_chain.ainvoke({
        "query": user_query
    })
    transformed_query = transformed_query_result['text']
    print(f"[DEBUG] 변환된 쿼리: {transformed_query}")
    
    # 문서 검색
    search_query = f"{transformed_query} (위치: {latitude}, {longitude}) 관련 태그: {user_categories}"

    docs = await retriever.ainvoke(search_query)

    # 거리 정렬
    sorted_docs = await sort_places_by_distance(docs, latitude, longitude)
    print(sorted_docs)

    schedule = await build_schedule_by_categories(sorted_docs, schedule_categories, start_time)
    print("schedule:", schedule )

    # 5. 스케줄을 텍스트로 변환
    schedule_text = await schedule_to_text(schedule)
    print("schedule_text:", schedule_text )

    # 기존 컨텍스트에 추가
    context = await get_context(session_id)
    context += f"\n{schedule_text}"

    # ✅ LLM 모델 설정
    chain = place_prompt | llm

    # LLM 호출
    result = await chain.ainvoke({
        "context": context,
        "location_context": f"현재 사용자의 위치는 위도 {latitude}, 경도 {longitude}입니다.",
        "time_context": f"현재 시간은 {current_time}입니다.",
        "question": user_query
    })
    print("result:", result)

    return result.content.strip() if result.content else "추천을 제공할 수 없습니다."