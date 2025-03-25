// 메인 페이지로 이동
function goToMain() {
    window.location.href = "https://lazy-traveler.store/pages/main/main.html";
}

document.addEventListener("DOMContentLoaded", async function() {
    try {
        const response = await axios.get("https://api.lazy-traveler.store/accounts/mypage/", {
            headers: {
                "Authorization": "Bearer " + localStorage.getItem("access_token"),
                "Content-Type": "application/json"
            }
        });

        const data = response.data;
        document.getElementById("username").textContent = data.username;
        
        // 태그 표시
        const tagsContainer = document.getElementById("tags");
        tagsContainer.innerHTML = ''; // 기존 태그 초기화
        
        if (data.tags) {
            const tags = data.tags.split(',');
            tags.forEach(tag => {
                const tagElement = document.createElement('div');
                tagElement.className = 'tag';
                tagElement.textContent = tag;
                tagsContainer.appendChild(tagElement);
            });
        }
    } catch (error) {
        console.error("오류 발생:", error);
        document.getElementById("username").textContent = "오류 발생";
        document.getElementById("tags").textContent = "오류 발생";
    }
});

// 로그아웃
function logout() {
    const refreshToken = localStorage.getItem("refresh_token");
    
    axios.post("https://api.lazy-traveler.store/accounts/logout/", {
        refresh_token: refreshToken
    }, {
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("access_token")
        }
    })
    .then(() => {
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("access_token");
        localStorage.removeItem("session_id");
        alert("로그아웃되었습니다.");
        window.location.href = "https://lazy-traveler.store/pages/login/login.html";
    })
    .catch(error => {
        console.error("로그아웃 오류:", error);
        alert("로그아웃 중 오류가 발생했습니다.");
    });
}

// 회원 탈퇴 모달 관련
function openWithdrawModal() {
    document.getElementById('withdraw-modal').style.display = 'block';
}

function closeWithdrawModal() {
    document.getElementById('withdraw-modal').style.display = 'none';
}

// 회원 탈퇴
function delete_account() {
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
        alert("엑세스 토큰이 없습니다. 로그인해주세요.");
        return;
    }

    axios.delete('https://api.lazy-traveler.store/accounts/delete_account/', {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    })
    .then(response => {
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("access_token");
        localStorage.removeItem("session_id");
        alert("회원 탈퇴가 완료되었습니다.");
        window.location.href = "https://lazy-traveler.store/pages/login/login.html";
    })
    .catch(error => {
        console.error("회원탈퇴 오류:", error);
        alert("회원탈퇴 중 오류가 발생했습니다.");
    });
}

// 비밀번호 변경 모달 관련
function openChangePasswordModal() {
    document.getElementById('change-password-modal').style.display = "block";
    // 에러 메시지 초기화
    hideAllPasswordErrors();
    // 입력 필드 초기화
    document.getElementById('current-password').value = '';
    document.getElementById('new-password').value = '';
    document.getElementById('confirm-password').value = '';
}

function closeChangePasswordModal() {
    document.getElementById('change-password-modal').style.display = "none";
    hideAllPasswordErrors();
}

function hideAllPasswordErrors() {
    document.getElementById('current-password-error').style.display = 'none';
    document.getElementById('same-password-error').style.display = 'none';
    document.getElementById('confirm-password-error').style.display = 'none';
}

function showPasswordErrors(errors) {
    hideAllPasswordErrors();
    errors.forEach(errorId => {
        document.getElementById(errorId).style.display = 'block';
    });
}

async function changePassword(event) {
    event.preventDefault();
    hideAllPasswordErrors();

    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    const errors = [];

    // 새 비밀번호 일치 여부 확인
    if (newPassword !== confirmPassword) {
        errors.push('confirm-password-error');
        showPasswordErrors(errors);
        return;
    }

    try {
        const response = await axios.post('https://api.lazy-traveler.store/accounts/update_password/', {
            current_password: currentPassword,
            new_password: newPassword
        }, {
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            }
        });

        alert("비밀번호가 성공적으로 변경되었습니다.");
        closeChangePasswordModal();
    } catch (error) {
        if (error.response?.data?.error) {
            if (error.response.data.error.includes('기존 비밀번호와 동일')) {
                errors.push('same-password-error');
            }
            if (error.response.data.error.includes('현재 비밀번호가 일치하지 않습니다')) {
                errors.push('current-password-error');
            }
            showPasswordErrors(errors);
        } else {
            alert("비밀번호 변경에 실패했습니다.");
        }
    }
}

// 태그 변경 모달 관련
function openChangeTagsModal() {
    document.getElementById('change-tags-modal').style.display = 'block';
    clearTagErrorMessage();
    getTags();
}

function closeChangeTagsModal() {
    document.getElementById('change-tags-modal').style.display = 'none';
    clearTagErrorMessage();
}

function showTagErrorMessage() {
    const errorMessage = document.querySelector('.tag-error-message');
    errorMessage.textContent = '최소 한 개 이상의 태그를 선택해주세요';
    errorMessage.classList.add('show');
}

function clearTagErrorMessage() {
    const errorMessage = document.querySelector('.tag-error-message');
    errorMessage.textContent = '';
    errorMessage.classList.remove('show');
}

const getTags = async () => {
    try {
        const response = await axios.get("https://api.lazy-traveler.store/accounts/update_tags/", {
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            }
        });

        const currentTags = response.data.tags ? response.data.tags.split(',') : [];
        const availableTags = ['공원', '관광명소', '베이커리', '베트남 음식', '브런치', '비건', '서점', '양식', '일식', '전시', '주점', '중식', '카페', '태국 음식', '피자', '한식', '햄버거'];

        // 태그 버튼 생성
        const availableTagsContainer = document.getElementById('available-tags');
        availableTagsContainer.innerHTML = '';
        
        availableTags.forEach(tag => {
            const tagButton = document.createElement('button');
            tagButton.className = 'tag-btn' + (currentTags.includes(tag) ? ' active' : '');
            tagButton.textContent = tag;
            tagButton.onclick = () => {
                tagButton.classList.toggle('active');
                checkTagChanges(currentTags);
            };
            availableTagsContainer.appendChild(tagButton);
        });

        // 현재 태그 표시
        const currentTagsContainer = document.getElementById('current-tags');
        currentTagsContainer.innerHTML = '';
        
        currentTags.forEach(tag => {
            const tagButton = document.createElement('button');
            tagButton.className = 'tag-btn active';
            tagButton.textContent = tag;
            tagButton.disabled = true;
            currentTagsContainer.appendChild(tagButton);
        });

        // 초기 상태에서 저장 버튼 비활성화
        document.getElementById('save-tags-btn').disabled = true;
    } catch (error) {
        console.error("태그 불러오기 실패:", error);
        alert("태그를 불러오는데 실패했습니다.");
    }
};

// 태그 변경 여부 확인 함수
function checkTagChanges(originalTags) {
    const selectedTags = Array.from(document.querySelectorAll('#available-tags .tag-btn.active'))
        .map(btn => btn.textContent);
    
    // 태그 개수가 다르거나, 선택된 태그 중 하나라도 원래 태그와 다른 경우
    const hasChanges = selectedTags.length !== originalTags.length ||
        selectedTags.some(tag => !originalTags.includes(tag)) ||
        originalTags.some(tag => !selectedTags.includes(tag));
    
    document.getElementById('save-tags-btn').disabled = !hasChanges;
}

document.getElementById('save-tags-btn').addEventListener('click', async () => {
    const selectedTags = Array.from(document.querySelectorAll('#available-tags .tag-btn.active'))
        .map(btn => btn.textContent);

    if (selectedTags.length === 0) {
        showTagErrorMessage();
        return;
    }

    try {
        const response = await axios.put("https://api.lazy-traveler.store/accounts/update_tags/", {
            tags: selectedTags.join(',')
        }, {
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
                'Content-Type': 'application/json'
            }
        });

        alert("태그가 성공적으로 변경되었습니다.");
        closeChangeTagsModal();
        location.reload();
    } catch (error) {
        console.error("태그 저장 실패:", error);
        alert("태그 저장에 실패했습니다.");
    }
});

// 태그 선택 시 에러 메시지 제거
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('tag-btn')) {
        clearTagErrorMessage();
    }
});