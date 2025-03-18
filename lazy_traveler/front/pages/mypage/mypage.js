document.addEventListener("DOMContentLoaded", async function() {
    try {
        const response = await axios.get("http://localhost:8000/accounts/mypage/", {
            headers: {
                "Authorization": "Bearer " + localStorage.getItem("access_token"), // ✅ 토큰 인증 필요
                "Content-Type": "application/json"
            }
        });

        const data = response.data;
        document.getElementById("username").textContent = data.username;
        document.getElementById("tags").textContent = data.tags ? data.tags : "없음";
    } catch (error) {
        console.error("오류 발생:", error);
        document.getElementById("username").textContent = "오류 발생";
        document.getElementById("tags").textContent = "오류 발생";
    }
});


// ✅ 로그아웃
function logout() {
    localStorage.removeItem("refresh_token");  // ✅ 리프레시 토큰 삭제
    localStorage.removeItem("access_token");  // ✅ 엑세스 토큰 삭제
    localStorage.removeItem("session_id");  // ✅ 세션 아이디 삭제
    alert("로그아웃 되었습니다.");
    window.location.href = "http://127.0.0.1:5500/lazy_traveler/front/pages/login/login.html";
}


// 회원 탈퇴
function delete_account() {
    const accessToken = localStorage.getItem('access_token');  // 로컬 스토리지에서 엑세스 토큰 가져오기

    if (!accessToken) {
        alert("엑세스 토큰이 없습니다. 로그인해주세요.");
        return;
    }

    // 사용자에게 회원 탈퇴 확인 요청
    const isConfirmed = confirm("정말 탈퇴하시겠습니까?🥹 탈퇴 시 모든 정보가 사라집니다❗️");
    if (!isConfirmed) {
        return;  // 사용자가 취소하면 함수 종료
    }

    // 계정 삭제 요청
    axios.delete('http://localhost:8000/accounts/delete_account/', {
        headers: {
            'Authorization': `Bearer ${accessToken}`  // Authorization 헤더에 엑세스 토큰 추가
        }
    })
    .then(response => {
        console.log('서버 응답:', response);  // 서버 응답 데이터 확인
        if (response.data.message) {
            alert(response.data.message);  // 응답 메시지 출력
        } else {
            console.log('응답 메시지 없음:', response.data);  // 응답 데이터가 예상과 다를 때 확인
        }

        // 토큰 삭제
        localStorage.removeItem("refresh_token");  // ✅ 리프레시 토큰 삭제
        localStorage.removeItem("access_token");  // ✅ 엑세스 토큰 삭제
        localStorage.removeItem("session_id");  // ✅ 세션 아이디 삭제
        
        // 로그인 페이지로 리다이렉트
        window.location.href = "http://127.0.0.1:5500/lazy_traveler/front/pages/login/login.html"; 
    })
    .catch(error => {
        console.error("회원탈퇴 오류:", error);
        alert("회원탈퇴 중 오류가 발생했습니다.");
    });
}



// 비밀번호 변경 모달 열기
function openChangePasswordModal() {
    document.getElementById('change-password-modal').style.display = "block";
}

// 비밀번호 변경 모달 닫기
function closeChangePasswordModal() {
    document.getElementById('change-password-modal').style.display = "none";
}

// 비밀번호 변경 처리
async function changePassword(event) {
    event.preventDefault();  // 폼이 제출되는 기본 동작을 막음

    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    // 새 비밀번호와 확인용 비밀번호가 같은지 체크
    if (newPassword !== confirmPassword) {
        alert("새 비밀번호와 비밀번호 확인이 일치하지 않습니다.");
        return;
    }

    try {
        const response = await axios.post('http://localhost:8000/accounts/update_password/', {
            current_password: currentPassword, // 현재 비밀번호 추가
            new_password: newPassword
        }, {
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
            }
        });

        if (response.status === 200) {
            alert("비밀번호가 성공적으로 변경되었습니다.");
            closeChangePasswordModal();  // 모달 닫기
        }
    } catch (error) {
        console.error('비밀번호 변경 오류:', error);
        alert(error.response?.data?.error || '비밀번호 변경에 실패했습니다.');
    }
}




// 모달 열기
function openChangeTagsModal() {
    document.getElementById('change-tags-modal').style.display = 'block';
    getTags();  // 모달 열 때 태그 불러오기
}

// 모달 닫기
function closeChangeTagsModal() {
    document.getElementById('change-tags-modal').style.display = 'none';
}

// 태그 변경 요청
const getTags = async () => {
    const accessToken = localStorage.getItem("access_token");  // 로컬 스토리지에서 엑세스 토큰 가져오기

    try {
        const response = await axios.get("http://127.0.0.1:8000/accounts/update_tags/", {
            headers: {
                'Authorization': `Bearer ${accessToken}`  // Authorization 헤더에 토큰 추가
            }
        });

        const currentTags = response.data.tags.split(',');  // 쉼표로 태그 나누기
        const availableTags = ['공원', '관광명소', '베이커리', '베트남 음식','브런치', '비건', '서점', '양식', '일식', '전시', '주점', '중식', '카페', '태국 음식', '피자', '한식', '햄버거']; 

        // 현재 태그 표시
        const currentTagsContainer = document.getElementById('current-tags');
        currentTagsContainer.innerHTML = '';  // 기존 태그 초기화
        currentTags.forEach(tag => {
            const tagElement = document.createElement('button');
            tagElement.classList.add('tag-button', 'selected');
            tagElement.textContent = tag;
            tagElement.disabled = true;  // 현재 태그는 클릭 불가
            currentTagsContainer.appendChild(tagElement);
        });

        // 추가할 수 있는 태그 표시
        const availableTagsContainer = document.getElementById('available-tags');
        availableTagsContainer.innerHTML = '';  // 기존 태그 초기화
        availableTags.forEach(tag => {
            const tagElement = document.createElement('button');
            tagElement.classList.add('tag-button');
            tagElement.textContent = tag;
            
            // 선택된 태그는 'selected' 클래스 추가
            if (currentTags.includes(tag)) {
                tagElement.classList.add('selected');
            }

            tagElement.onclick = () => tagElement.classList.toggle('selected');
            availableTagsContainer.appendChild(tagElement);
        });
    } catch (error) {
        console.error("태그 불러오기 실패:", error);
    }
};

const saveTags = async () => {
    const accessToken = localStorage.getItem("access_token");  // 로컬 스토리지에서 엑세스 토큰 가져오기

    const selectedTags = [];
    document.querySelectorAll('#available-tags .tag-button.selected').forEach(button => {
        selectedTags.push(button.textContent);
    });

    // 선택된 태그들을 쉼표로 구분된 문자열로 변환
    const tagsString = selectedTags.join(',');

    try {
        const response = await axios.put("http://127.0.0.1:8000/accounts/update_tags/", {
            tags: tagsString  // 쉼표로 구분된 태그 문자열
        }, {
            headers: {
                'Authorization': `Bearer ${accessToken}`,  // Authorization 헤더에 토큰 추가
                'Content-Type': 'application/json'  // JSON 형식으로 요청
            }
        });
        alert(response.data.message);
    } catch (error) {
        console.error("태그 저장 실패:", error.response?.data || error);
        alert("태그 저장 실패.");
    }
};

document.getElementById('save-tags-btn').addEventListener('click', saveTags);

// 페이지 로딩 시 태그 불러오기
window.onload = getTags;