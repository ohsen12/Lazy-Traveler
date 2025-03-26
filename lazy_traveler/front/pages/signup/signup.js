document.addEventListener('DOMContentLoaded', () => {
    // 필요한 DOM 요소들 선택
    const idInput = document.querySelector('input[placeholder="ID를 입력해주세요"]');
    const passwordInput = document.querySelector('input[placeholder="비밀번호를 입력해주세요"]');
    const password2Input = document.querySelector('input[placeholder="비밀번호를 다시 입력해주세요"]');
    const duplicateCheckBtn = document.querySelector('.duplicate-check');
    const signupBtn = document.querySelector('.signup-btn');
    const tagButtons = document.querySelectorAll('.tag-grid button');
    const idMessage = document.querySelector('.id-message');
    const passwordMessage = document.querySelector('.password-message');
    const tagMessage = document.querySelector('.tag-message');
    
    let isIdChecked = false; // ID 중복 확인 여부
    const selectedTags = new Set(); // 선택된 태그들을 저장할 Set

    // 메시지 표시 함수
    function showMessage(element, message, isSuccess) {
        element.textContent = message;
        element.className = 'message ' + (isSuccess ? 'success' : 'error');
    }

    // 메시지 초기화 함수
    function clearMessage(element) {
        element.textContent = '';
        element.className = 'message';
    }

    // ID 중복 확인
    duplicateCheckBtn.addEventListener('click', async () => {
        const username = idInput.value.trim();
        
        if (!username) {
            showMessage(idMessage, '사용할 수 없는 ID입니다', false);
            return;
        }

        try {
            const response = await axios.post('https://api.lazy-traveler.store/accounts/check_username/', {
                username: username
            }, {
                headers: {
                    'Content-Type': 'application/json'
                },
                withCredentials: true  // 이 부분 추가해보기
            })

            if (response.status === 200) {
                showMessage(idMessage, '사용 가능한 ID입니다', true);
                isIdChecked = true;
            }
        } catch (error) {
            if (error.response?.status === 409) {
                showMessage(idMessage, '사용할 수 없는 ID입니다', false);
            } else {
                showMessage(idMessage, 'ID 중복 확인 중 오류가 발생했습니다', false);
            }
            isIdChecked = false;
        }
    });

    // 비밀번호 확인 함수
    function validatePasswords() {
        const password = passwordInput.value;
        const password2 = password2Input.value;

        if (password2 && password !== password2) {
            showMessage(passwordMessage, '입력하신 비밀번호가 일치하지 않습니다', false);
            return false;
        } else if (password2) {
            clearMessage(passwordMessage);
            return true;
        }
        return false;
    }

    // 비밀번호 입력 필드 이벤트
    password2Input.addEventListener('input', validatePasswords);

    // 태그 선택 이벤트
    tagButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tagName = button.textContent;
            
            if (selectedTags.has(tagName)) {
                selectedTags.delete(tagName);
                button.style.backgroundColor = 'transparent';
                button.style.color = '#333';
                button.style.borderColor = '#333';
            } else {
                selectedTags.add(tagName);
                button.style.backgroundColor = '#4E5052';
                button.style.color = 'white';
                button.style.borderColor = '#4E5052';
            }
            
            // 태그가 선택되면 에러 메시지 제거
            if (selectedTags.size > 0) {
                clearMessage(tagMessage);
            }
        });
    });

    // 회원가입 처리
    signupBtn.addEventListener('click', async () => {
        const username = idInput.value.trim();
        const password = passwordInput.value;
        const password2 = password2Input.value;

        // 입력값 검증
        if (!username || !password || !password2) {
            alert('모든 필수 항목을 입력해주세요.');
            return;
        }

        if (!isIdChecked) {
            showMessage(idMessage, 'ID 중복 확인을 해주세요', false);
            return;
        }

        if (!validatePasswords()) {
            return;
        }

        // 태그 선택 여부 확인
        if (selectedTags.size === 0) {
            showMessage(tagMessage, '최소 한 개 이상의 태그를 선택해주세요', false);
            return;
        }

        try {
            const response = await axios.post('https://api.lazy-traveler.store/accounts/signup/', {
                username: username,
                password: password,
                password2: password2,
                tags: Array.from(selectedTags).join(',')
            }, {
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.status === 201 || response.status === 200) {
                alert('회원가입이 완료되었습니다.');
                // 로그인 페이지로 이동
                window.location.href = 'https://lazy-traveler.store/pages/login/login.html';
            }
        } catch (error) {
            console.error('회원가입 오류:', error);
            if (error.response?.data?.detail) {
                showMessage(passwordMessage, error.response.data.detail, false);
            } else {
                alert('회원가입 중 오류가 발생했습니다.');
            }
        }
    });

    // ID 입력 필드 변경 시 중복 확인 상태 초기화
    idInput.addEventListener('input', () => {
        isIdChecked = false;
        clearMessage(idMessage);
    });

    // 로그인 페이지 이동 링크
    document.querySelector('.footer a').addEventListener('click', (e) => {
        e.preventDefault();
        window.location.href = 'https://lazy-traveler.store/pages/login/login.html';
    });
});