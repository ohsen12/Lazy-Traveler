# Python 3.9 이미지를 기반으로 시작합니다.
FROM python:3.10-slim

# 시스템 종속성 설치 (예: libpq-dev는 PostgreSQL 데이터베이스를 위한 필수 패키지입니다)
RUN apt-get update && apt-get install -y libpq-dev

# 작업 디렉토리를 /app으로 설정
WORKDIR /app

# 의존성 목록을 복사하여 설치합니다.
COPY requirements.txt /app/

# 필요 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 코드 복사
COPY . /app/

# Django 환경 변수 설정
ENV PYTHONUNBUFFERED 1

# 데이터베이스와 같은 외부 서비스가 준비될 때까지 기다리기 위한 패키지 설치
# RUN pip install wait-for-it

# Django의 기본 포트인 8000번을 공개합니다.
EXPOSE 8000

# Django 서버 실행 명령
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]