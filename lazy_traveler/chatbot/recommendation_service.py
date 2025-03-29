from datetime import datetime
from .prompt import place_prompt 
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
    format_place_results_to_html,
    filter_open_places_with_llm,
    search_places
    )
from .openai_chroma_config import function_vector_store, llm



async def get_recommendation(user_query, session_id=None, username=None, latitude=None, longitude=None):
    #유저 질문 기능 분류(llm)
    question_type = await classify_question_with_llm(user_query)

    if question_type == "function":
        function_results = function_vector_store.similarity_search_with_score(
            query=user_query,
            k=1,
            filter={"type":"qa" }
        )
        # print("function_results[0][1]:",function_results[0][1])
        if not function_results or function_results[0][1] > 1.1:
            return "기능 관련 정보를 찾을 수 없습니다."

        answer = function_results[0][0].metadata.get("answer", "")
        return answer
    
    if question_type == "place":
        latitude = float(latitude)
        longitude = float(longitude)
        place_results = await search_places(user_query, latitude, longitude) #place 검색 및 거리 계산
        # print("place_results:", place_results)

        # 결과 포맷팅 (HTML로 변환)
        place_results_html = await format_place_results_to_html(place_results) #place 결과 html로 변환 
        return place_results_html

    if question_type == "unknown":
        error_message = "죄송합니다.😢 기능, 장소, 일정 스케줄링에 대해 문의해 주세요. 😊예) 회원가입 하는 법‘, ‘스케줄링 해줘‘, ‘맛집 추천해줘’"
        return error_message
    
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    start_time = now

    if latitude is None or longitude is None:
        latitude, longitude = 37.5704, 126.9831


    #스케줄링 시간대
    schedule_type, schedule_categories = await determine_schedule_template(now) #시간 기반 스케줄링표 지정
    # print("schedule_categories:", schedule_categories)
    if schedule_type == "불가시간":
        return "스케줄링 불가시간입니다. 오전 8시부터 오후 11시까지만 스케줄링이 가능합니다."
    
    # 태그 가져오기
    user_tags = await get_user_tags(username) # 유저 태그 가져오기
    preferred_tag_mapping = await get_preferred_tags_by_schedule(user_tags, schedule_categories) #대분류 중 사용자가 태그만 선택

    #태그 기반으로 장소 검색
    docs = await search_places_by_preferred_tags(user_query, preferred_tag_mapping)

    # 거리 정렬
    sorted_docs = await sort_places_by_distance(docs, latitude, longitude)
    # print("sorted_docs:",sorted_docs)

    #운영시간 확인
    filtered_docs = await filter_open_places_with_llm(sorted_docs, now)
    # print("filtered_docs:", filtered_docs)

    #선호 태그와 일정 카테고리 기반 스케줄 생성
    schedule = await build_schedule_by_categories_with_preferences(
        filtered_docs, schedule_categories, preferred_tag_mapping, start_time
    )
    # print("schedule1:", schedule )

    #스케줄을 텍스트로 변환
    schedule_text = await schedule_to_text(schedule)
    # print("schedule_text:", schedule_text )

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
    # print("result:", result)

    if isinstance(result, str):
        return result.strip()
    elif hasattr(result, "content"):
        return result.content.strip()
    else:
        return "추천을 제공할 수 없습니다."