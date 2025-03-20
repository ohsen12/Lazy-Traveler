let map, marker, geocoder, infowindow;
let socket;
let currentSessionId = null; 

kakao.maps.load(() => {
    var container = document.getElementById('map');
    var options = { 
        center: new kakao.maps.LatLng(37.5704, 126.9831), // 기본 위치: 종각역
        level: 3 
    };
    map = new kakao.maps.Map(container, options);
    geocoder = new kakao.maps.services.Geocoder();

    // 기본 마커 (종각역)
    marker = new kakao.maps.Marker({
        position: new kakao.maps.LatLng(37.5704, 126.9831),
        map: map
    });

    // 정보창 추가
    infowindow = new kakao.maps.InfoWindow({
        content: `<div style="padding:5px;">📍 종각역</div>`
    });
    infowindow.open(map, marker);

    // 지도 클릭 시 마커 이동 및 주소 업데이트
    kakao.maps.event.addListener(map, "click", function(event) {
        var position = event.latLng;
        marker.setPosition(position);
        getAddressFromCoords(position);

    });
});


// 현재 위치 가져오기
function getUserLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                var lat = position.coords.latitude;
                var lng = position.coords.longitude;
                var newPosition = new kakao.maps.LatLng(lat, lng);

                marker.setPosition(newPosition);
                map.setCenter(newPosition);
                getAddressFromCoords(newPosition);
            },
            function(error) {
                alert("위치 정보를 가져올 수 없습니다. 권한을 확인하세요.");
            }
        );
    } else {
        alert("이 브라우저에서는 위치 정보가 지원되지 않습니다.");
    }
}


// 현재 주소 가져오기
function getAddressFromCoords(coords) {
    geocoder.coord2Address(coords.getLng(), coords.getLat(), function(result, status) {
        if (status === kakao.maps.services.Status.OK) {
            var address = result[0].road_address ? result[0].road_address.address_name : result[0].address.address_name;
            document.getElementById("location-info").innerText = `📍 현재 위치: ${address} (${coords.getLat().toFixed(5)}, ${coords.getLng().toFixed(5)})`;

            infowindow.setContent(`<div style="padding:5px;">📍 ${address}</div>`);
            infowindow.open(map, marker);
        }
    });
}

//웹 소켓
function connectWebSocket() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        console.log("✅ WebSocket 이미 연결됨");
        return;
    }

    // 로컬 스토리지에서 토큰을 가져와 Authorization 헤더에 추가
    const token = localStorage.getItem("access_token");
    const url = token ? `ws://localhost:8000/ws/chat/?token=${token}` : "ws://localhost:8000/ws/chat/";

    socket = new WebSocket(url);

    socket.onopen = function () {
        console.log("✅ WebSocket 연결 성공!");
    };

    socket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        console.log("GPT-4o 응답:", data.response);

        // 응답을 화면에 추가
        appendMessage(data.response, "bot-response");

        // 세션 ID 업데이트 (새 세션이 있으면 로컬 스토리지에 저장)
        if (data.session_id) {
            localStorage.setItem("session_id", data.session_id);
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

    if (socket.readyState === WebSocket.OPEN) {
        appendMessage(userMessage, "user-message");

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

// 채팅 메세지 화면 추가

// 리프레시
function refreshChat() {
    localStorage.removeItem("session_id");  // ✅ 세션 아이디 삭제
    currentSessionId = null;  // ✅ 메모리에서도 초기
    window.location.reload(); // 페이지 새로고침화
    console.log("챗봇 화면이 새로고침되었습니다.");
}


// 로그아웃
function logout() {
    localStorage.removeItem("refresh_token");  // ✅ 리프레시 토큰 삭제
    localStorage.removeItem("access_token");  // ✅ 엑세스 토큰 삭제
    localStorage.removeItem("session_id");  // ✅ 세션 아이디 삭제
    alert("로그아웃 되었습니다.");
    window.location.href = "http://127.0.0.1:5500/lazy_traveler/front/pages/login/login.html";
}

// 대화 내역 불러오기
function loadChatHistory() {
    console.log("대화 기록을 불러오는 중...");

    axios.get("http://127.0.0.1:8000/chatbot/chat_history/", {
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + localStorage.getItem("access_token"),
        }
    })
    .then(response => {
        console.log("대화 기록 불러오기 성공:", response.data);
        const data = response.data;
        const historyList = document.getElementById("chat-history");
        historyList.innerHTML = ""; // 기존 목록 초기화

        // 날짜별로 세션 내역 추가
        data.forEach(group => {
            const date = group.date;
            console.log(`날짜: ${date}`);

            let dateItem = document.createElement("li");
            dateItem.textContent = `${date} ▼`;
            dateItem.classList.add("accordion");
            historyList.appendChild(dateItem);

            // 각 날짜의 세션 목록을 숨겨놓기
            let sessionList = document.createElement("li");
            sessionList.classList.add("accordion-content");

            group.sessions.forEach(session => {
                console.log(`세션 ID: ${session.session_id}, 첫 메시지: ${session.first_message}`);

                let sessionItem = document.createElement("li");
                sessionItem.classList.add("history-item");

                sessionItem.innerHTML = `
                    <span style="color:gray;">${session.created_at}</span>
                    <strong>${session.first_message}</strong>
                `;

                // 세션 클릭 시 해당 세션의 대화 내역 불러오기
                sessionItem.onclick = () => loadSessionMessages(session.session_id);

                sessionList.appendChild(sessionItem);
            });

            historyList.appendChild(sessionList);

            // 아코디언 기능 추가
            dateItem.onclick = function() {
                this.classList.toggle("active");
                
                // ▲과 ▼을 서로 바꿔줍니다
                if (this.textContent.includes("▲")) {
                    this.textContent = `${date} ▼`;  // ▲ -> ▼로 변경
                } else {
                    this.textContent = `${date} ▲`;  // ▼ -> ▲로 변경
                }

                if (sessionList.style.display === "block") {
                    sessionList.style.display = "none";
                } else {
                    sessionList.style.display = "block";
                }
            };
        });
    })
    .catch(error => {
        console.error("대화 기록 불러오기 실패:", error);
    });
}

function initializeMap() {
    const container = document.getElementById("map");

    // #map 요소가 없으면 실행 안 함
    if (!container) {
        console.error("🛑 지도 컨테이너가 없습니다! #map을 찾을 수 없음.");
        return;
    }

    kakao.maps.load(() => {
        var options = {
            center: new kakao.maps.LatLng(37.5704, 126.9831), // 기본 위치: 종각역
            level: 3
        };

        map = new kakao.maps.Map(container, options);
        geocoder = new kakao.maps.services.Geocoder();

        // 기본 마커 (종각역)
        marker = new kakao.maps.Marker({
            position: new kakao.maps.LatLng(37.5704, 126.9831),
            map: map
        });

        // 정보창 추가
        infowindow = new kakao.maps.InfoWindow({
            content: `<div style="padding:5px;">📍 종각역</div>`
        });
        infowindow.open(map, marker);

        // 지도 클릭 시 마커 이동 및 주소 업데이트
        kakao.maps.event.addListener(map, "click", function(event) {
            var position = event.latLng;
            marker.setPosition(position);
            getAddressFromCoords(position);
        });

        console.log("✅ Kakao 지도 초기화 완료!");
    });
}

function loadSessionMessages(session_id) {
    console.log(`세션 ${session_id}의 메시지를 불러오는 중...`);

    currentSessionId = session_id;
    localStorage.setItem("session_id", session_id);

    axios.get(`http://127.0.0.1:8000/chatbot/chat_history/?session_id=${session_id}`, {
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + localStorage.getItem("access_token"),
        }
    })
    .then(response => {
        console.log(`세션 ${session_id} 메시지 불러오기 성공:`, response.data);
        const messages = response.data;

        const chatBox = document.getElementById("chat-box");
        chatBox.innerHTML = ""; // 기존 메시지 삭제

        // ✅ 기본 UI 요소 추가
        const defaultMessage = document.createElement("div");
        defaultMessage.classList.add("message", "bot-message");
        defaultMessage.innerHTML = `
            안녕하세요? [User_ID]님. Lazy Traveler예요.<br>
            어느 장소에서 여행하는 루트를 추천해드릴까요?
        `;
        chatBox.appendChild(defaultMessage);

        const locationSection = document.createElement("div");
        locationSection.classList.add("location-section");
        locationSection.innerHTML = `
            <button class="location-button" onclick="getUserLocation()">
                📍 현재 내 위치로 이동
            </button>
            <p id="location-info">📍 현재 위치: 종각역 (37.5704, 126.9831)</p>
            <div id="map"></div>
            <p>고객님의 현재 위치는 종각역 입니다. <br>
                핀을 움직여, 일정을 시작하실 위치를 변경해 보세요! </p>
        `;
        chatBox.appendChild(locationSection);

        // ✅ 📌 지도 초기화 함수 실행
        setTimeout(() => {
            initializeMap(); // #map이 추가된 후 실행해야 함
        }, 100); // 100ms 후 실행 (DOM 업데이트 시간 확보)

        // ✅ 메시지 목록 추가
        messages.forEach(chat => {
            appendMessage(chat.message, "user-message");
            appendMessage(chat.response, "bot-response");
        });
    })
    .catch(error => {
        console.error("대화 기록 불러오기 실패:", error);
    });
}

function appendMessage(message, type) {
    const chatBox = document.getElementById("chat-box");

    // 새로운 메시지 컨테이너 생성
    const messageContainer = document.createElement("div");
    messageContainer.classList.add("message", type);
    messageContainer.textContent = message; // textContent로 텍스트 추가
    messageContainer.style.opacity = "0";  // 처음에는 투명하게 설정

    // 채팅박스에 새 메시지 추가
    chatBox.appendChild(messageContainer);

    // 약간의 지연 후 메시지를 표시 (부드러운 애니메이션 가능)
    setTimeout(() => {
        messageContainer.style.opacity = "1";
        messageContainer.style.transition = "opacity 0.3s ease-in-out"; // 0.3초 동안 자연스럽게 나타나게 함
    }, 50); // 50ms 후 표시

    // 메시지가 추가된 후, 스크롤을 최신 메시지로 이동
    chatBox.scrollTop = chatBox.scrollHeight;
}

// ✅ DOM 로드 시 웹소켓 연결 및 이벤트 리스너 추가
document.addEventListener("DOMContentLoaded", function () {
    connectWebSocket(); // 웹소켓 연결
    document.getElementById("send-btn").addEventListener("click", sendMessage);
    document.getElementById("user-message").addEventListener("keypress", function (event) {
        if (event.key === "Enter") {
            sendMessage();
        }
    });
});



// 사용자 메시지 추가
function appendUserMessage(message) {
    const chatBox = document.getElementById("chat-box");
    const userMessage = document.createElement("li");
    userMessage.classList.add("message", "user-message");
    userMessage.textContent = message;
    chatBox.appendChild(userMessage);
}


// 챗봇 응답에 로딩 메시지 추가
function appendBotResponseWithLoading() {
    const chatBox = document.getElementById("chat-box");
    const botResponse = document.createElement("li");
    botResponse.classList.add("message", "bot-response");
    
    const loadingMessage = document.createElement("span");
    loadingMessage.id = "bot-loading-message";
    loadingMessage.textContent = "🤖 로딩 중...";  // 로딩 메시지 내용

    botResponse.appendChild(loadingMessage);
    chatBox.appendChild(botResponse);
}

// 챗봇 응답 메시지 업데이트
function updateBotResponse(responseMessage) {
    const chatBox = document.getElementById("chat-box");
    const lastBotResponse = chatBox.lastElementChild;
    
    if (lastBotResponse && lastBotResponse.classList.contains("bot-response")) {
        lastBotResponse.textContent = responseMessage;  // 응답 메시지로 변경
        
    }
}


// 페이지가 새로 고쳐지기 전에 localStorage에서 session_id를 삭제
window.addEventListener('beforeunload', function() {
    localStorage.removeItem("session_id");
    currentSessionId = null;
});



// 페이지가 로드될 때 대화 기록 불러오기
window.onload = function() {
    loadChatHistory();
};