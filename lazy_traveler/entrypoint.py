import os
import time
import subprocess
from dotenv import load_dotenv  # dotenv 라이브러리 로드

# .env 파일에서 환경 변수 로드
load_dotenv()

# 데이터베이스가 준비될 때까지 대기 (PostgreSQL이 실행되기 전에 Django가 실행되는 문제 방지)
db_host = os.getenv("POSTGRES_HOST")
db_port = os.getenv("POSTGRES_PORT")

print("Waiting for database to be ready...")
while True:
    result = subprocess.run(
        ["nc", "-z", db_host, db_port], capture_output=True
    )
    if result.returncode == 0:
        break
    time.sleep(1)

print("Database is ready!")

# 벡터 DB 구축 스크립트 실행
print("Running vector database build script...")
subprocess.run(["python", "chatbot/build_vector_store.py"], check=True)

# Django 마이그레이션 
print("Running makemigrations for all apps...")
subprocess.run(["python", "manage.py", "makemigrations"], check=True)

# Django 마이그레이션
print("Applying migrations...")
subprocess.run(["python", "manage.py", "migrate"], check=True)

# Django 서버 실행
print("Starting Django server...")
subprocess.run([
    "gunicorn",
    "lazy_traveler.asgi:application",
    "-k", "uvicorn.workers.UvicornWorker",
    "--bind", "0.0.0.0:8000",
    "--workers", "3",
    "--threads", "2",
], check=True)


