from datetime import datetime
from langchain.chains import LLMChain
from .prompt import function_prompt, place_prompt, query_prompt
from .utils import (
    get_context,
    get_user_tags,
    sort_places_by_distance,
    schedule_to_text,
    build_schedule_by_categories_with_preferences,
    determine_schedule_template,
    get_preferred_tags_by_schedule,
    search_places_by_preferred_tags,
    classify_question_with_llm,
    format_place_results_to_html
    )
from .openai_chroma_config import function_vector_store,place_vector_store, retriever, llm


async def get_recommendation(user_query, session_id=None, username=None, latitude=None, longitude=None):
    now = datetime.now()
    # now = datetime(2025, 3, 27, 16, 30, 0)
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    start_time = now

    if latitude is None or longitude is None:
        latitude, longitude = 37.5704, 126.9831

    question_type = await classify_question_with_llm(user_query)
    print

    if question_type == "function":
        function_results = function_vector_store.similarity_search_with_score(
            query=user_query,
            k=1,
            filter={"type": "qa"}
        )
        print("function_results[0][1]:",function_results[0][1])
        if not function_results or function_results[0][1] > 1.0:
            return "기능 관련 정보를 찾을 수 없습니다."

        answer = function_results[0][0].metadata.get("answer", "")
        return answer
    
    if question_type == "place":
        place_results = place_vector_store.similarity_search_with_score(
            query=user_query,
            k=3,
            filter={"type": "place"}
        )
        
        answer = await format_place_results_to_html(place_results)
        return answer

    if question_type == "unknown":
        return "죄송합니다. 조금 더 구체적으로 말씀해 주시겠어요?"

    #스케줄링 시간대
    schedule_type, schedule_categories = await determine_schedule_template(now)
    print("schedule_categories:", schedule_categories)
    if schedule_type == "불가시간":
        return "스케줄링 불가시간입니다. 오전 8시부터 오후 11시까지만 스케줄링이 가능합니다."
    
    # 태그 가져오기
    user_tags = await get_user_tags(username)
    preferred_tag_mapping = await get_preferred_tags_by_schedule(user_tags, schedule_categories)

    # query_transform_chain = LLMChain(llm=llm, prompt=query_prompt)
    # # 1. 비동기 실행 후 결과 저장
    # transformed_query_result = await query_transform_chain.ainvoke({"query": user_query})

    # # 2. 변환된 쿼리 추출
    # transformed_query = transformed_query_result['text']
    # print(f"[DEBUG] 변환된 쿼리: {transformed_query}")

    # 문서 검색
    # search_query = f"{user_query} (위치: {latitude}, {longitude}) 관련 태그: {user_tags}"

    docs = await search_places_by_preferred_tags(user_query, preferred_tag_mapping)

    # 거리 정렬
    sorted_docs = await sort_places_by_distance(docs, latitude, longitude)
    # print(sorted_docs)

    schedule = await build_schedule_by_categories_with_preferences(
        sorted_docs, schedule_categories, preferred_tag_mapping, start_time
    )
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