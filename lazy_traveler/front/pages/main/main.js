let map, marker, geocoder, infowindow;
let socket;
let currentSessionId = null;
let hasStartedChat = false; // 대화 시작 여부를 추적하는 변수 추가

document.addEventListener("DOMContentLoaded", () => {
    kakao.maps.load(() => {
        initKakaoMap();  
        initChatUI();
        connectWebSocket();
        showCoachmark();
        // 페이지 로드 시 스크롤을 최상단으로 이동
        setTimeout(scrollChatToTop, 100);
    });
});

function initKakaoMap() {
    console.log("✅ Kakao Maps 로드 완료");

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

    console.log("✅ Kakao 지도 초기화 완료");
    
    // 지도 초기화 완료 후 채팅창 스크롤을 최상단으로 이동
    setTimeout(() => {
        scrollChatToTop();
    }, 100);
}

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
    loadChatHistory();
    showCoachmark();

    document.getElementById("send-btn").addEventListener("click", sendMessage);
    document.getElementById("user-message").addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault(); // Enter 키의 기본 동작 방지
            sendMessage();
        }
    });
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
                    저는 종로에서 여행하는 일정을 스케줄링 해드립니다.<br>
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

        const { username = "고객님", tags = "" } = response.data;
        const tagList = tags ? tags.split(',') : [];

        // 시스템 메시지 동적으로 변경
        if (botMessage) {
            botMessage.innerHTML = `
                안녕하세요? ${username}님. Lazy Traveler예요.<br>
                저는 종로에서 여행하는 일정을 스케줄링 해드립니다.<br>
                ${tagList.length > 0 ? `고객님의 [${tagList.join(", ")}] 태그를 기반으로 코스를 제안해 드릴까요?` : 
                "어느 장소에서 여행하는 루트를 추천해드릴까요?"}
            `;
        }

        // 스크롤을 최상단으로 이동
        setTimeout(scrollChatToTop, 100);

    } catch (error) {
        console.error("오류 발생:", error);
    }
});



//웹 소켓
function connectWebSocket() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        console.log("✅ WebSocket 이미 연결됨");
        return;
    }

    // 로컬 스토리지에서 토큰을 가져와 Authorization 헤더에 추가
    const token = localStorage.getItem("access_token");
    const url = token 
    ? `wss://api.lazy-traveler.store/ws/chat/?token=${token}` 
    : "wss://api.lazy-traveler.store/ws/chat/";

    socket = new WebSocket(url);

    socket.onopen = function () {
        console.log("✅ WebSocket 연결 성공!");
    };

    socket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        console.log("GPT-4 응답:", data.response);

        // 로딩 메시지 업데이트
        updateBotResponse(data.response);

        // 세션 ID 업데이트
        if (data.session_id) {
            localStorage.setItem("session_id", data.session_id);
            // 응답을 받은 후 채팅 히스토리를 업데이트
            reloadChatHistory();
        }
    };

    socket.onerror = function (event) {
        console.log("❌ WebSocket 에러 발생:", event);
        if (event && event.message) {
            console.log("Error Message:", event.message);
        }
    };

    socket.onclose = function () {
        console.log("🔄 WebSocket 종료됨. 3초 후 재연결 시도...");
        setTimeout(connectWebSocket, 10000);  // 3초 후 재연결
    };
}


// 사용자 메시지 보내기
function sendMessage() {
    const userMessage = document.getElementById("user-message").value.trim();
    if (!userMessage) return;

    if (!socket) {
        console.warn("🚨 WebSocket이 초기화되지 않았습니다. 연결을 시도합니다...");
        return;
    }

    if (socket.readyState === WebSocket.OPEN) {
        hasStartedChat = true; // 대화 시작 표시
        appendMessage(userMessage, "user-message");
        appendBotResponseWithLoading();

        const position = marker.getPosition();
        const requestData = {
            message: userMessage,
            latitude: position.getLat().toFixed(6),
            longitude: position.getLng().toFixed(6),
            session_id: localStorage.getItem("session_id") || "",
            new_session: !localStorage.getItem("session_id")
        };

        socket.send(JSON.stringify(requestData));
    } else {
        console.warn("🚨 WebSocket이 닫혀 있어 메시지를 보낼 수 없습니다.");
    }

    document.getElementById("user-message").value = "";
}


// 리프레시
function refreshChat() {
    localStorage.removeItem("session_id");  // ✅ 세션 아이디 삭제
    currentSessionId = null;  // ✅ 메모리에서도 초기
    hasStartedChat = false;  // 대화 시작 상태 초기화
    window.location.reload(); // 페이지 새로고침화
    console.log("챗봇 화면이 새로고침되었습니다.");
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
    console.log("대화 기록을 불러오는 중...");

    const token = localStorage.getItem("access_token");

    // 토큰이 없는 경우 로그인 메시지와 버튼을 표시
    if (!token) {
        displayLoginMessage();
        return;  // 토큰이 없으면 대화 내역을 불러오지 않음
    }

    // 토큰이 있는 경우 대화 내역 불러오기
    axios.get("https://api.lazy-traveler.store/chatbot/chat_history/", {
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        }
    })
    .then(response => {
        console.log("대화 기록 불러오기 성공:", response.data);
        const data = response.data;
        const historyList = document.getElementById("chat-history");
        historyList.innerHTML = ""; // 기존 목록 초기화

        // 데이터 처리
        data.forEach(group => {
            const { date, sessions } = group;
            console.log(`날짜: ${date}`);

            // 날짜 항목 생성
            const dateItem = createDateItem(date);
            historyList.appendChild(dateItem);

            // 세션 목록 항목 생성
            const sessionList = createSessionList(sessions);
            historyList.appendChild(sessionList);

            // 아코디언 기능 추가
            toggleAccordion(dateItem, sessionList);
        });
    })
    .catch(error => {
        console.error("대화 기록 불러오기 실패:", error);
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
        console.log(`세션 ID: ${session.session_id}, 첫 메시지: ${session.first_message}`);

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
    console.log(`세션 ${session_id}의 메시지를 불러오는 중...`);

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
        const { username = "고객님", tags = "" } = userResponse.data;
        const tagList = tags ? tags.split(',') : [];

        // 채팅 내역을 불러옵니다.
        return axios.get(`https://api.lazy-traveler.store/chatbot/chat_history/?session_id=${session_id}`, {
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            }
        }).then(response => {
            console.log(`세션 ${session_id} 메시지 불러오기 성공:`, response.data);
            const messages = response.data;

            const chatBox = document.getElementById("chat-box");
            chatBox.innerHTML = ""; // 기존 메시지 삭제

            // 기본 UI 요소 추가
            const defaultMessage = document.createElement("div");
            defaultMessage.classList.add("message", "bot-message");
            defaultMessage.innerHTML = `
                안녕하세요? ${username}님. Lazy Traveler예요.<br>
                저는 종로에서 여행하는 일정을 스케줄링 해드립니다.<br>
                ${tagList.length > 0 ? `고객님의 [${tagList.join(", ")}] 태그를 기반으로 코스를 제안해 드릴까요?` : 
                "어느 장소에서 여행하는 루트를 추천해드릴까요?"}
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
        console.error("데이터 불러오기 실패:", error);
    });
}

function appendMessage(message, type) {
    const chatBox = document.getElementById("chat-box");

    // 새로운 메시지 컨테이너 생성
    const messageContainer = document.createElement("div");
    messageContainer.classList.add("message", type);
    messageContainer.textContent = message;
    
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

    // 로딩 메시지를 포함한 마지막 응답 찾기
    if (lastBotResponse && lastBotResponse.classList.contains("bot-response")) {
        const loadingMessage = lastBotResponse.querySelector("#bot-loading-message");

        // 로딩 메시지 있는 경우, 해당 span의 텍스트를 응답 메시지로 변경
        if (loadingMessage) {
            loadingMessage.textContent = responseMessage;  // 로딩 메시지를 응답 메시지로 교체
        }
    }
    scrollChatToBottom();
}

// ✅ DOM 로드 시 웹소켓 연결 및 이벤트 리스너 추가
document.addEventListener("DOMContentLoaded", function () {
    connectWebSocket(); // 웹소켓 연결
    document.getElementById("send-btn").addEventListener("click", sendMessage);
    document.getElementById("user-message").addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault(); // Enter 키의 기본 동작 방지
            sendMessage();
        }
    });
});



// ✅ 페이지가 새로 고쳐지기 전에 localStorage에서 session_id를 삭제
window.addEventListener('beforeunload', function() {
    localStorage.removeItem("session_id");
    currentSessionId = null;
});



// 페이지가 로드될 때 대화 기록 불러오기
window.onload = function() {
    loadChatHistory();
    hasStartedChat = false;
    // 페이지 로드 시 스크롤을 최상단으로 이동
    setTimeout(scrollChatToTop, 100);
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
    console.log("채팅 히스토리 다시 로드 중...");

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
        console.log("채팅 히스토리 업데이트 성공:", response.data);
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
    .catch(error => {
        console.error("채팅 히스토리 업데이트 실패:", error);
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
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}
