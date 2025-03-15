document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById('signup-form');
    const messageDiv = document.getElementById('signup-message');
    const tagButtons = document.querySelectorAll('.tag-button');
    const selectedTags = new Set();

    tagButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault(); // 기본 동작 방지 (폼 제출 방지)
            const tag = button.dataset.tag;
            if (selectedTags.has(tag)) {
                selectedTags.delete(tag);
                button.classList.remove('selected');
            } else {
                selectedTags.add(tag);
                button.classList.add('selected');
            }
            console.log('현재 선택된 태그:', Array.from(selectedTags)); // 선택된 태그 디버깅
        });
    });
    

    // 폼 제출 시 동작하는 이벤트
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault(); // 기본 폼 제출 동작 방지
            console.log('회원가입 폼 제출 시작'); // 디버깅용 로그

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const password2 = document.getElementById('password2').value;

            // 비밀번호 확인
            if (password !== password2) {
                messageDiv.textContent = '비밀번호가 일치하지 않습니다.';
                messageDiv.style.color = 'red';
                return;
            }

            // 선택된 태그 출력 (디버깅용)
            console.log('선택된 태그:', Array.from(selectedTags));



            try {
                const response = await axios.post('http://localhost:8000/accounts/signup/', {
                    username,
                    password,
                    password2,
                    tags: Array.from(selectedTags).join(',')  // 태그를 쉼표로 구분된 문자열로 변환
                }, { 
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                // 응답 처리
                console.log('회원가입 응답:', response.status);

                if (response.status >= 200 && response.status < 300) {
                    messageDiv.textContent = '회원가입 성공!';
                    messageDiv.style.color = 'green';

                    signupForm.reset(); // 폼 리셋 (페이지 이동 전에 실행)
                    console.log("회원가입 성공, 리다이렉트 준비 중");
                

                    console.log("리다이렉트 시도 중...");
                    window.location.href = 'http://127.0.0.1:5500/lazy_traveler/front/pages/login/login.html';
                }
            } catch (error) {
                console.error("에러 발생:", error);
                if (error.response) {
                    messageDiv.textContent = error.response.data.detail || '회원가입 실패';
                } else {
                    messageDiv.textContent = '서버와 연결할 수 없습니다.';
                }
                messageDiv.style.color = 'red';
            }
        });
    }
});