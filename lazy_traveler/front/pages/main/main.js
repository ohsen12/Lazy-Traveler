let map, marker, geocoder, infowindow;
let socket;
let currentSessionId = null;
let hasStartedChat = false; // 대화 시작 여부를 추적하는 변수 추가
let isProcessingMessage = false; // 메시지 처리 중 상태를 추적하는 변수 추가
let messageCount = 0; // 메시지 전송 횟수를 추적하는 변수
let lastMessageDate = new Date().toDateString(); // 마지막 메시지 전송 날짜

// DOMContentLoaded 이벤트에서 카카오맵 초기화
document.addEventListener("DOMContentLoaded", () => {
    // 카카오맵 로드
    kakao.maps.load(() => {
        const container = document.getElementById('map');
        const options = {
            center: new kakao.maps.LatLng(37.5704, 126.9831),
            level: 3
        };

        map = new kakao.maps.Map(container, options);
        geocoder = new kakao.maps.services.Geocoder();

        marker = new kakao.maps.Marker({
            position: new kakao.maps.LatLng(37.5704, 126.9831),
            map: map
        });

        infowindow = new kakao.maps.InfoWindow({
            content: `<div style="padding:5px;">📍 종각역</div>`
        });
        infowindow.open(map, marker);

        kakao.maps.event.addListener(map, "click", (event) => {
            const position = event.latLng;
            marker.setPosition(position);
            getAddressFromCoords(position);
        });

        // 지도 초기화 후 UI 초기화
        initChatUI();
        connectWebSocket();
        showCoachmark();
    });
});

// 현재 위치 가져오기
function getUserLocation() {
    if (!marker) {
        alert("⛔️ 지도가 아직 준비되지 않았습니다.");
        return;
    }

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                const newPosition = new kakao.maps.LatLng(lat, lng);

                marker.setPosition(newPosition);
                map.setCenter(newPosition);
                getAddressFromCoords(newPosition);
            },
            (error) => {
                alert("위치 정보를 가져올 수 없습니다.");
            }
        );
    } else {
        alert("이 브라우저는 위치 정보가 지원되지 않습니다.");
    }
}


// 현재 주소 가져오기
function getAddressFromCoords(coords) {
    geocoder.coord2Address(coords.getLng(), coords.getLat(), (result, status) => {
        if (status === kakao.maps.services.Status.OK) {
            const address = result[0].road_address
                ? result[0].road_address.address_name
                : result[0].address.address_name;

            document.getElementById("location-info").innerText = `📍 현재 위치: ${address} (${coords.getLat().toFixed(5)}, ${coords.getLng().toFixed(5)})`;

            infowindow.setContent(`<div style="padding:5px;">📍 ${address}</div>`);
            infowindow.open(map, marker);
        }
    });
}

function initChatUI() {
    connectWebSocket();
    
    const sendButton = document.getElementById("send-btn");
    const messageInput = document.getElementById("user-message");
    
    // 기존 이벤트 리스너 제거
    sendButton.removeEventListener("click", processAndSendMessage);
    messageInput.removeEventListener("keydown", handleEnterKey);
    
    // 새로운 이벤트 리스너 등록
    sendButton.addEventListener("click", () => {
        if (!isProcessingMessage) {
            processAndSendMessage();
        }
    });
    
    // Enter 키 이벤트를 별도 함수로 분리
    messageInput.addEventListener("keydown", handleEnterKey);
}

// Enter 키 처리를 위한 별도 함수
function handleEnterKey(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        if (!isProcessingMessage) {
            processAndSendMessage();
        }
    }
}

//첫시작 대화창 및 user-menu숨기기
document.addEventListener("DOMContentLoaded", async function() {
    try {
        // 토큰 확인
        const token = localStorage.getItem("access_token");
        const botMessage = document.querySelector(".message.bot-message");
        const logoutButton = document.querySelector(".logout");

        // 토큰이 없으면 비로그인자의 메시지 처리
        if (!token) {
            if (botMessage) {
                botMessage.innerHTML = `
                    안녕하세요? 고객님. Lazy Traveler에요.<br>
                    종로에서 즐길 수 있는 코스를 작성해드릴게요.<br>
                    보다 정확한 답변을 원하시면, 로그인 하신 후 질문해주세요!
                `;
            }
            // 로그인하지 않은 경우, logout 버튼만 숨기기
            if (logoutButton) {
                logoutButton.style.display = "none";
            }
            // 스크롤을 최상단으로 이동
            setTimeout(scrollChatToTop, 100);
            return;
        }

        // 로그인한 경우 logout 버튼 표시
        if (logoutButton) {
            logoutButton.style.display = "block";
        }

        // 토큰이 있을 경우 서버에서 유저 데이터 가져오기
        const response = await axios.get("https://api.lazy-traveler.store/accounts/mypage/", {
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            }
        });

        // username이 [User_ID]인 경우 '고객'으로 대체
        let { username = "고객", tags = "" } = response.data;
        username = username === "[User_ID]" ? "고객" : username;
        const tagList = tags ? tags.split(',') : [];

        // 시스템 메시지 동적으로 변경
        if (botMessage) {
            botMessage.innerHTML = `
                안녕하세요? ${username}님. Lazy Traveler예요.<br>
                종로에서 즐길 수 있는 코스를 작성해드릴게요.<br>
                ${tagList.length > 0 ? `고객님의 [${tagList.join(", ")}] 태그를 기반으로 코스를 제안해 드릴까요?` : 
                "어느 장소에서 여행하는 루트를 추천해드릴까요?"}
            `;
        }

        // 스크롤을 최상단으로 이동
        setTimeout(scrollChatToTop, 100);

    } catch (error) {
        // 오류 발생 시 기본 메시지 표시
        const botMessage = document.querySelector(".message.bot-message");
        if (botMessage) {
            botMessage.innerHTML = `
                안녕하세요? 고객님. Lazy Traveler예요.<br>
                종로에서 즐길 수 있는 코스를 작성해드릴게요.<br>
                어느 장소에서 여행하는 루트를 추천해드릴까요?
            `;
        }
        setTimeout(scrollChatToTop, 100);
    }
});



//웹 소켓
function connectWebSocket() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        return;
    }

    // 로컬 스토리지에서 토큰을 가져와 Authorization 헤더에 추가
    const token = localStorage.getItem("access_token");
    const url = token 
    ? `wss://api.lazy-traveler.store/ws/chat/?token=${token}` 
    : "wss://api.lazy-traveler.store/ws/chat/";

    socket = new WebSocket(url);

    socket.onopen = function () {
        // WebSocket 연결 성공
    };

    socket.onmessage = function (event) {
        const data = JSON.parse(event.data);

        // 로딩 메시지 업데이트
        updateBotResponse(data.response);

        // 세션 ID 업데이트
        if (data.session_id) {
            localStorage.setItem("session_id", data.session_id);
            // 응답을 받은 후 채팅 히스토리를 업데이트
            reloadChatHistory();
        }

        // 응답이 완료되면 입력창과 전송 버튼 다시 활성화
        const messageInput = document.getElementById("user-message");
        const sendButton = document.getElementById("send-btn");
        messageInput.disabled = false;
        messageInput.style.backgroundColor = "rgba(246, 248, 250, 0.95)";
        sendButton.disabled = false;
        sendButton.style.opacity = "1";
        isProcessingMessage = false;
    };

    socket.onerror = function (event) {
        // WebSocket 연결 오류
    };

    socket.onclose = function () {
        setTimeout(connectWebSocket, 10000);  // 10초 후 재연결
    };
}

// 메시지 전송 횟수 초기화 함수
function resetMessageCount() {
    const currentDate = new Date().toDateString();
    const lastDate = localStorage.getItem('lastMessageDate');
    
    if (currentDate !== lastDate) {
        localStorage.setItem('messageCount', '0');
        localStorage.setItem('lastMessageDate', currentDate);
    }
}

// 메시지 전송 가능 여부 확인 함수
function canSendMessage() {
    const currentDate = new Date().toDateString();
    const lastDate = localStorage.getItem('lastMessageDate');
    const count = parseInt(localStorage.getItem('messageCount') || '0');
    
    // 날짜가 변경되었다면 카운트 초기화
    if (currentDate !== lastDate) {
        resetMessageCount();
        return true;
    }
    
    // 하루 100회 초과 시 false 반환
    if (count >= 100) {
        alert('하루에 100번까지 채팅이 가능해요! 🥹');
        return false;
    }
    
    return true;
}

// 리프레시 버튼 클릭 횟수 확인 함수
function canRefresh() {
    const currentDate = new Date().toDateString();
    const lastDate = localStorage.getItem('lastRefreshDate');
    const refreshCount = parseInt(localStorage.getItem('refreshCount') || '0');
    
    // 날짜가 변경되었다면 카운트 초기화
    if (currentDate !== lastDate) {
        localStorage.setItem('refreshCount', '0');
        localStorage.setItem('lastRefreshDate', currentDate);
        return true;
    }
    
    // 하루 5회 초과 시 false 반환
    if (refreshCount >= 5) {
        alert('현재 리프레시 버튼은 하루 5번만 클릭 가능해요! 🥹');
        return false;
    }
    
    return true;
}

// 리프레시
function refreshChat() {
    if (!canRefresh()) {
        return;
    }
    
    // 리프레시 카운트 증가
    const currentCount = parseInt(localStorage.getItem('refreshCount') || '0');
    localStorage.setItem('refreshCount', (currentCount + 1).toString());
    
    localStorage.removeItem("session_id");  // ✅ 세션 아이디 삭제
    currentSessionId = null;  // ✅ 메모리에서도 초기
    hasStartedChat = false;  // 대화 시작 상태 초기화
    window.location.reload(); // 페이지 새로고침화
}


// 로그아웃
function logout() {
    localStorage.removeItem("refresh_token");  // ✅ 리프레시 토큰 삭제
    localStorage.removeItem("access_token");  // ✅ 엑세스 토큰 삭제
    localStorage.removeItem("session_id");  // ✅ 세션 아이디 삭제
    alert("로그아웃 되었습니다.");
    window.location.href = "https://lazy-traveler.store/pages/main/main.html";
}

// 대화 내역 불러오기
function loadChatHistory() {
    return new Promise((resolve) => {
        const token = localStorage.getItem("access_token");

        if (!token) {
            displayLoginMessage();
            resolve();
            return;
        }

        axios.get("https://api.lazy-traveler.store/chatbot/chat_history/", {
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            }
        })
        .then(response => {
            const data = response.data;
            const historyList = document.getElementById("chat-history");
            historyList.innerHTML = "";

            data.forEach(group => {
                const { date, sessions } = group;
                const dateItem = createDateItem(date);
                historyList.appendChild(dateItem);

                const sessionList = createSessionList(sessions);
                historyList.appendChild(sessionList);

                toggleAccordion(dateItem, sessionList);
            });
            resolve();
        })
        .catch(() => {
            resolve();
        });
    });
}

// 로그인 메시지 및 버튼을 표시하는 함수
function displayLoginMessage() {
    const historyList = document.getElementById("chat-history");
    historyList.innerHTML = ""; // 기존 목록 초기화

    const loginMessage = document.createElement("li");
    loginMessage.classList.add("login-message");  // 로그인 메시지 클래스 추가

    loginMessage.innerHTML = `
        <p class="login-text">로그인 하신 후, <br> 이용 가능합니다. <button class="login-btn">로그인 하러 가기</button></p>
    `;

    const loginButton = loginMessage.querySelector(".login-btn");
    loginButton.onclick = () => window.location.href = "https://lazy-traveler.store/pages/login/login.html";  // 로그인 페이지로 이동

    historyList.appendChild(loginMessage);
}

// 날짜 항목 생성
function createDateItem(date) {
    const dateItem = document.createElement("li");
    dateItem.textContent = `${date} ▼`;
    dateItem.classList.add("accordion");
    return dateItem;
}

// 세션 목록 항목 생성
function createSessionList(sessions) {
    const sessionList = document.createElement("li");
    sessionList.classList.add("accordion-content");

    sessions.forEach(session => {
        const sessionItem = document.createElement("li");
        sessionItem.classList.add("history-item");
        sessionItem.innerHTML = `
            <span>${session.created_at}</span>
            <strong>${session.first_message}</strong>
        `;

        // 현재 세션이 선택된 세션인지 확인
        if (session.session_id === currentSessionId) {
            sessionItem.classList.add("selected");
        }

        // 세션 클릭 시 해당 세션의 대화 내역 불러오기
        sessionItem.onclick = () => {
            // 모든 세션에서 selected 클래스 제거
            document.querySelectorAll(".history-item").forEach(item => {
                item.classList.remove("selected");
            });
            // 클릭된 세션에 selected 클래스 추가
            sessionItem.classList.add("selected");
            loadSessionMessages(session.session_id);
        };

        sessionList.appendChild(sessionItem);
    });

    return sessionList;
}

// 아코디언 기능 처리
function toggleAccordion(dateItem, sessionList) {
    dateItem.onclick = function() {
        this.classList.toggle("active");

        // ▲과 ▼을 서로 바꿔줍니다
        this.textContent = this.textContent.includes("▲") 
            ? `${this.textContent.replace("▲", "▼")}`
            : `${this.textContent.replace("▼", "▲")}`;

        sessionList.style.display = sessionList.style.display === "block" ? "none" : "block";
    };
}

//대화 버튼 비활성화 
function toggleChatInput(disable) {
    const userMessageInput = document.getElementById("user-message");
    const sendButton = document.getElementById("send-btn");

    if (disable) {
        userMessageInput.disabled = true;
        userMessageInput.value = "이전 대화에서는 추가 대화가 불가능합니다."; // 메시지 고정
        userMessageInput.style.color = "#888"; // 회색으로 변경 (비활성화 느낌)
        sendButton.disabled = true;
        sendButton.style.opacity = "0.5"; // 버튼 비활성화 효과
        sendButton.style.backgroundColor = "#FFFFFF"; // 버튼 색상 변경
    } else {
        userMessageInput.disabled = false;
        userMessageInput.value = ""; // 입력 가능할 때 기존 메시지 삭제
        userMessageInput.style.color = "#000"; // 검정색으로 복원
        sendButton.disabled = false;
        sendButton.style.opacity = "1"; // 버튼 활성화 효과
        sendButton.style.backgroundColor = ""; // 원래 스타일로 복원
    }
}

function loadSessionMessages(session_id) {
    currentSessionId = session_id;
    localStorage.setItem("session_id", session_id);

    // 먼저 사용자 정보를 가져옵니다.
    const token = localStorage.getItem("access_token");
    
    // 사용자 정보를 가져온 후 채팅 내역을 불러옵니다.
    axios.get("https://api.lazy-traveler.store/accounts/mypage/", {
        headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        }
    })
    .then(userResponse => {
        // username이 [User_ID]인 경우 '고객'으로 대체
        let { username = "고객", tags = "" } = userResponse.data;
        username = username === "[User_ID]" ? "고객" : username;
        const tagList = tags ? tags.split(',') : [];

        // 채팅 내역을 불러옵니다.
        return axios.get(`https://api.lazy-traveler.store/chatbot/chat_history/?session_id=${session_id}`, {
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            }
        }).then(response => {
            const messages = response.data;

            const chatBox = document.getElementById("chat-box");
            chatBox.innerHTML = ""; // 기존 메시지 삭제

            // 기본 UI 요소 추가
            const defaultMessage = document.createElement("div");
            defaultMessage.classList.add("message", "bot-message");
            defaultMessage.innerHTML = `
                안녕하세요? ${username}님. Lazy Traveler예요.<br>
                종로에서 즐길 수 있는 코스를 작성해드릴게요.<br>
                고객님의 태그를 기반으로 코스를 제안해 드릴까요?
            `;
            chatBox.appendChild(defaultMessage);

            const locationSection = document.createElement("div");
            locationSection.classList.add("location-section");
            locationSection.innerHTML = `
                <p>고객님의 현재 위치는 종각역입니다. <br>
                    핀을 움직여, 일정을 시작하실 위치를 변경해 보세요! </p>
            `;
            chatBox.appendChild(locationSection);

            toggleChatInput(true);

            // 메시지 목록 추가
            messages.forEach(chat => {
                appendMessage(chat.message, "user-message");
                appendMessage(chat.response, "bot-response");
            });

            scrollChatToTop();
            hasStartedChat = false; // 새로운 세션을 로드할 때 대화 시작 상태 초기화
        });
    })
    .catch(error => {
        console.error("데이터를 불러올 수 없습니다.");
    });
}

function appendMessage(message, type) {
    const chatBox = document.getElementById("chat-box");

    // 새로운 메시지 컨테이너 생성
    const messageContainer = document.createElement("div");
    messageContainer.classList.add("message", type);
    
    // ```html 태그 제거 및 메시지 정제
    let cleanMessage = message;
    if (typeof message === 'string') {
        cleanMessage = message.replace(/```html\n?/g, '').replace(/```$/g, '');
    }

    // HTML 여부 판단
    const parser = new DOMParser();
    const doc = parser.parseFromString(cleanMessage, "text/html");
    const isHTML = Array.from(doc.body.childNodes).some(
        node => node.nodeType === 1  // ELEMENT_NODE
    );

    if (isHTML) {
        // 실제 DOM 요소로 대체
        messageContainer.innerHTML = cleanMessage;
    } else {
        // 일반 텍스트만 갱신
        messageContainer.textContent = cleanMessage;
    }
    
    // 채팅박스에 새 메시지 추가
    chatBox.appendChild(messageContainer);

    // 대화가 시작된 경우에만 스크롤을 최하단으로 이동
    if (hasStartedChat) {
        scrollChatToBottom();
    }
}


// 사용자 메시지 추가
function appendUserMessage(message) {
    const chatBox = document.getElementById("chat-box");
    const userMessage = document.createElement("li");
    userMessage.classList.add("message", "user-message");
    userMessage.textContent = message;
    chatBox.appendChild(userMessage);
    scrollChatToBottom();
}

// 챗봇 응답에 로딩 메시지 추가
function appendBotResponseWithLoading() {
    const chatBox = document.getElementById("chat-box");

    // 로딩 메시지 컨테이너 생성
    const botResponse = document.createElement("ul");
    botResponse.classList.add("message", "bot-response");
    
    const loadingMessage = document.createElement("span");
    loadingMessage.id = "bot-loading-message";
    loadingMessage.textContent = "🤖 로딩 중...";  // 로딩 메시지 내용

    botResponse.appendChild(loadingMessage);
    chatBox.appendChild(botResponse);
    scrollChatToBottom();
}

// 챗봇 응답 메시지 업데이트
function updateBotResponse(responseMessage) {
    const chatBox = document.getElementById("chat-box");
    const lastBotResponse = chatBox.lastElementChild;
    
    // ```html 태그 제거 및 메시지 정제
    let cleanMessage = responseMessage;
    if (typeof responseMessage === 'string') {
        cleanMessage = responseMessage.replace(/```html\n?/g, '').replace(/```$/g, '');
    }

    // 로딩 메시지를 포함한 마지막 응답 찾기
    if (lastBotResponse && lastBotResponse.classList.contains("bot-response")) {
        const loadingMessage = lastBotResponse.querySelector("#bot-loading-message");

        if (loadingMessage) {
            // HTML 여부 판단
            const parser = new DOMParser();
            const doc = parser.parseFromString(cleanMessage, "text/html");
            const isHTML = Array.from(doc.body.childNodes).some(
                node => node.nodeType === 1  // ELEMENT_NODE
            );

            if (isHTML) {
                // 실제 DOM 요소로 대체
                loadingMessage.outerHTML = cleanMessage;
            } else {
                // 일반 텍스트만 갱신
                loadingMessage.textContent = cleanMessage;
            }
        }
    }
    scrollChatToBottom();
}

// ✅ 페이지가 새로 고쳐지기 전에 localStorage에서 session_id를 삭제
window.addEventListener('beforeunload', function() {
    localStorage.removeItem("session_id");
    currentSessionId = null;
});



// 페이지가 로드될 때 대화 기록 불러오기
window.onload = async function() {
    hasStartedChat = false;
    
    // 채팅 히스토리를 먼저 로드
    await loadChatHistory();
    
    // 모든 초기화가 완료된 후 스크롤을 최상단으로 이동
    setTimeout(() => {
        scrollChatToTop();
    }, 200);
};

// 마이페이지 이동
function goToMypage() {
    const token = localStorage.getItem("access_token");
    if (!token) {
        // 비로그인 상태일 때 로그인 페이지로 이동
        window.location.href = "https://lazy-traveler.store/pages/login/login.html";
    } else {
        // 로그인 상태일 때 마이페이지로 이동
        window.location.href = "https://lazy-traveler.store/pages/mypage/mypage.html";
    }
}

// 채팅 히스토리 다시 로드하는 함수
function reloadChatHistory() {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    // 현재 열려있는 아코디언의 날짜를 저장
    const openAccordions = [];
    document.querySelectorAll('.accordion').forEach(accordion => {
        if (accordion.classList.contains('active')) {
            openAccordions.push(accordion.textContent.split(' ')[0]); // 날짜 부분만 저장
        }
    });

    axios.get("https://api.lazy-traveler.store/chatbot/chat_history/", {
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        }
    })
    .then(response => {
        const data = response.data;
        const historyList = document.getElementById("chat-history");
        historyList.innerHTML = "";

        data.forEach(group => {
            const { date, sessions } = group;
            
            // 날짜 항목 생성
            const dateItem = createDateItem(date);
            historyList.appendChild(dateItem);

            // 세션 목록 항목 생성
            const sessionList = createSessionList(sessions);
            historyList.appendChild(sessionList);

            // 이전에 열려있던 아코디언이면 다시 열기
            if (openAccordions.includes(date)) {
                dateItem.classList.add('active');
                dateItem.textContent = `${date} ▲`;
                sessionList.style.display = 'block';
            }

            // 아코디언 기능 추가
            toggleAccordion(dateItem, sessionList);
        });
    })
    .catch(() => {
        // 에러 처리
    });
}

// ✅ 코치마크 관련 함수
function showCoachmark() {
    const accessToken = localStorage.getItem('access_token');
    const hasSeenCoachmark = localStorage.getItem('has_seen_coachmark');
    
    if (!accessToken && !hasSeenCoachmark) {
        document.querySelector('.coachmark-container').classList.add('show');
        localStorage.setItem('has_seen_coachmark', 'true');
    }
}

function hideCoachmark() {
    document.querySelector('.coachmark-container').classList.remove('show');
}

// 페이지 로드 시 코치마크 표시
document.addEventListener('DOMContentLoaded', () => {
    showCoachmark();
    
    // 코치마크 닫기 버튼 이벤트 리스너
    document.querySelector('.coachmark-close').addEventListener('click', hideCoachmark);
});

// 메인 페이지로 이동
function goToMain() {
    window.location.href = "https://lazy-traveler.store/pages/main/main.html";
}

// 채팅창 스크롤을 최상단으로 이동시키는 함수
function scrollChatToTop() {
    const chatBox = document.getElementById("chat-box");
    if (chatBox) {
        chatBox.scrollTop = 0;
    }
}

// 채팅창 스크롤을 최하단으로 이동시키는 함수
function scrollChatToBottom() {
    const chatBox = document.getElementById("chat-box");
    if (chatBox && hasStartedChat) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

// 메시지 처리 및 전송을 담당하는 새로운 함수
function processAndSendMessage() {
    const messageInput = document.getElementById("user-message");
    const message = messageInput.value.trim();
    const sendButton = document.getElementById("send-btn");
    
    if (!message || isProcessingMessage) return;
    
    // 메시지 전송 가능 여부 확인
    if (!canSendMessage()) {
        return;
    }
    
    isProcessingMessage = true;
    
    // localStorage에 메시지 카운트 증가
    const currentCount = parseInt(localStorage.getItem('messageCount') || '0');
    localStorage.setItem('messageCount', (currentCount + 1).toString());
    
    // 입력창과 전송 버튼 비활성화
    messageInput.disabled = true;
    messageInput.style.backgroundColor = "#f0f0f0";
    sendButton.disabled = true;
    sendButton.style.opacity = "0.5";
    
    // 실제 메시지 전송
    if (!socket) {
        isProcessingMessage = false;
        // 입력창과 전송 버튼 다시 활성화
        messageInput.disabled = false;
        messageInput.style.backgroundColor = "rgba(246, 248, 250, 0.95)";
        sendButton.disabled = false;
        sendButton.style.opacity = "1";
        return;
    }

    if (socket.readyState === WebSocket.OPEN) {
        hasStartedChat = true;
        appendMessage(message, "user-message");
        appendBotResponseWithLoading();

        const position = marker.getPosition();
        const requestData = {
            message: message,
            latitude: position.getLat().toFixed(6),
            longitude: position.getLng().toFixed(6),
            session_id: localStorage.getItem("session_id") || "",
            new_session: !localStorage.getItem("session_id")
        };

        // 메시지를 전송한 후에 입력창 초기화
        requestAnimationFrame(() => {
            messageInput.value = "";
            messageInput.style.height = "24px"; // 높이 초기화
            messageInput.scrollTop = 0; // 스크롤 위치 초기화
            messageInput.selectionStart = 0; // 커서 위치 처음으로
            messageInput.selectionEnd = 0; // 선택 영역 초기화
        });

        socket.send(JSON.stringify(requestData));
    } else {
        isProcessingMessage = false;
        // 입력창과 전송 버튼 다시 활성화
        messageInput.disabled = false;
        messageInput.style.backgroundColor = "rgba(246, 248, 250, 0.95)";
        sendButton.disabled = false;
        sendButton.style.opacity = "1";
    }
}

// sendMessage 함수를 processAndSendMessage로 대체
function sendMessage() {
    if (!isProcessingMessage) {
        processAndSendMessage();
    }
}

// 스케줄 메시지 자동 전송 함수
function sendScheduleMessage() {
    const messageInput = document.getElementById("user-message");
    messageInput.value = "스케줄링 해줘";
    processAndSendMessage();
}
