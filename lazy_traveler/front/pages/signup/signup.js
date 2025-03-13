document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById('signup-form');
    const messageDiv = document.getElementById('signup-message');
    const tagButtons = document.querySelectorAll('.tag-button');
    const selectedTags = new Set();

    // 버튼 클릭 이벤트 등록
    tagButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tag = button.dataset.tag; // data-tag 속성 값 가져오기
            if (selectedTags.has(tag)) {
                selectedTags.delete(tag);
                button.classList.remove('selected');
            } else {
                selectedTags.add(tag);
                button.classList.add('selected');
            }
        });
    });

    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const password2 = document.getElementById('password2').value;

            if (password !== password2) {
                messageDiv.textContent = '비밀번호가 일치하지 않습니다.';
                messageDiv.style.color = 'red';
                return;
            }

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

                if (response.status >= 200 && response.status < 300) {
                    messageDiv.textContent = '회원가입 성공!';
                    messageDiv.style.color = 'green';
                    signupForm.reset();
                    setTimeout(() => {
                        window.location.href = 'http://127.0.0.1:5500/lazy_traveler/front/pages/login/login.html';
                    }, 2000);
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
