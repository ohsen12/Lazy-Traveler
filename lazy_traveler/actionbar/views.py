from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

# 챗봇 앱에서 스케줄 관련 모델과 시리얼라이저 재사용
from datetime import datetime
#from chatbot.models import Schedule 
#from chatbot.serializers import ScheduleSerializer  


#리프레시 버튼 클릭 시 대화 내역을 초기화하는 View
class RefreshConversationView(APIView):
    permission_classes = [permissions.AllowAny] #로그인/비로그인 모두 접근

    def post(self,request):       
        """
        POST요청 시, 서버측에서 대화내역을 초기화 했다고 가정 후 프론트에서도 대화창을 비우도록 안내내
        """
        #로그인 된 사용자인지 확인
        if request.user.is_authenticated:   
            #로그인 유저인 경우:
            #대화 내역은 이미 ConversationLog에 저장 되어있다고 가정
            #'초기화 완료' 응답만 전달
            return Response({'detail':'대화내역이 초기화되었습니다.'})
        else: 
            #비로그인 유저:
            #대화내역 저장은 안 됨, 응답만 전달
            return Response({'detail':'대화내역이 초기화되었습니다.'})


#스케줄러 버튼 클릭시 스케줄 조회를 담당 
class ScheduleMenuView(APIView):

    permission_classes = [permissions.IsAuthenticated] #로그인 된 사용자만 스케줄러 조회 가능능

    def get(self,request):
        
        #로그인 유저인 경우: DB에서 스케줄 목록 조회
        user = request.user
        #schedules = Schedule.objects.filter(user=user).order_by('created_at') #생성 날짜를 기준으로 조회. 

        #일자별로 정리 
        day_groups = {}

        #for schedule in schedules:
        #    day_str = schedule.created_at.strftime("%Y-%m-%d")

            # if day_str not in day_groups:
            #     day_groups[day_str] = []   

            #     #해당 날짜 key에 스케줄의 정보를 딕셔너리 형태로 추가.
            #     #스케줄의 id, title, schedule_data, created_at 정보를 포함.
            #     day_groups[day_str].append({
            #         "id": schedule.id,
            #         "title": schedule.title,
            #         "schedule_data": schedule.schedule_data,
            #         "created_at": schedule.created_at
            #     })
    
        #최종적으로 날짜별로 그룹화된 스케줄 데이터를 JSON응답으로 반환.
        return Response({"schedule_by_day": day_groups}, status=status.HTTP_200_OK)   
