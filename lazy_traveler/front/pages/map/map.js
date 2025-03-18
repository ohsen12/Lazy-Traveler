let map, marker, geocoder, infowindow;
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


// 리프레시
function refreshChat() {
    document.getElementById('chat-box').innerHTML = ''; // 채팅 내용 초기화
    localStorage.removeItem("session_id");  // ✅ 세션 아이디 삭제
    currentSessionId = null;  // ✅ 메모리에서도 초기화
    console.log("챗봇 화면이 새로고침되었습니다.");
}


// 마이페이지로 이동
function goToMypage() {
    window.location.href = 'http://127.0.0.1:5500/lazy_traveler/front/pages/mypage/mypage.html'// mypage.html로 리다이렉트
}


// 로그아웃
function logout() {
    localStorage.removeItem("refresh_token");  // ✅ 리프레시 토큰 삭제
    localStorage.removeItem("access_token");  // ✅ 엑세스 토큰 삭제
    localStorage.removeItem("session_id");  // ✅ 세션 아이디 삭제
    alert("로그아웃 되었습니다.");
    window.location.href = "http://127.0.0.1:5500/lazy_traveler/front/pages/login/login.html";
}


function appendMessage(message, type) {
    const chatBox = document.getElementById("chat-box");

    // 새로운 메시지 컨테이너 생성
    const messageContainer = document.createElement("div");
    messageContainer.classList.add("message", type);
    messageContainer.textContent = message; // textContent로 텍스트 추가

    // 채팅박스에 새 메시지 추가
    chatBox.appendChild(messageContainer);

    // 메시지가 추가된 후, 스크롤을 최신 메시지로 이동
    chatBox.scrollTop = chatBox.scrollHeight;
}


document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("send-btn").addEventListener("click", sendMessage);
    document.getElementById("user-message").addEventListener("keypress", function (event) {
        if (event.key === "Enter") {
            sendMessage();
        }
    });
});


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
            dateItem.textContent = `📅 ${date}`;
            dateItem.classList.add("accordion");
            historyList.appendChild(dateItem);

            // 각 날짜의 세션 목록을 숨겨놓기
            let sessionList = document.createElement("ul");
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


// 특정 세션의 전체 메시지 불러오기
function loadSessionMessages(session_id) {
    console.log(`세션 ${session_id}의 메시지를 불러오는 중...`);

    // 세션 ID를 로컬 스토리지에 저장
    currentSessionId = session_id;  // 세션 아이디 업데이트
    localStorage.setItem("session_id", session_id);  // 로컬스토리지에도 저장

    axios.get(`http://127.0.0.1:8000/chatbot/chat_history/?session_id=${session_id}`, {
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + localStorage.getItem("access_token"),
        }
    })
    .then(response => {
        console.log(`세션 ${session_id} 메시지 불러오기 성공:`, response.data);
        const messages = response.data;

        // 채팅박스를 초기화하여 새로운 세션의 대화만 표시
        const chatBox = document.getElementById("chat-box");
        chatBox.innerHTML = ""; // 기존 대화 내용 초기화

        // 메시지 목록을 appendMessage로 하나씩 추가
        messages.forEach(chat => {
            // 사용자 메시지 추가
            appendMessage(chat.message, "user-message");

            // 응답 메시지 추가
            appendMessage(chat.response, "bot-response");
        });
    })
    .catch(error => {
        console.error("대화 기록 불러오기 실패:", error);
        if (error.response) {
            console.error("서버 응답 상태 코드:", error.response.status);
            console.error("서버 응답 데이터:", error.response.data);
        }
    });
}


// 메시지 보내기
function sendMessage() {
    const userMessage = document.getElementById("user-message").value;
    if (userMessage.trim() === "") return;

    appendUserMessage(userMessage);  // 사용자 메시지 추가

    const position = marker.getPosition();
    const requestData = {
        message: userMessage,
        latitude: position.getLat().toFixed(6),
        longitude: position.getLng().toFixed(6),
    };

    // ✅ 새 세션 여부 확인
    let sessionId = currentSessionId || localStorage.getItem("session_id");
    const isNewSession = !sessionId || sessionId === ""; 

    if (isNewSession) {
        sessionId = "";  // 새로운 세션 ID 생성 요청
        localStorage.removeItem("session_id"); // ✅ 기존 세션 완전 삭제
        currentSessionId = null;
    }

    requestData.session_id = sessionId;
    requestData.new_session = isNewSession;

    // 챗봇 응답 영역에 로딩 중 메시지 추가
    appendBotResponseWithLoading();

    axios.post("http://127.0.0.1:8000/chatbot/chat/", requestData, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem("access_token")}`
        }
    })
    .then(response => {
        const botResponse = response.data.response;
        
        // 로딩 메시지를 실제 응답 메시지로 바꿈
        updateBotResponse(botResponse);

        // ✅ 새로운 session_id 저장
        if (response.data.session_id) {
            localStorage.setItem("session_id", response.data.session_id);
            currentSessionId = response.data.session_id;
        }

        // 메시지 전송 후 대화 히스토리 갱신
        loadChatHistory();  // 대화 히스토리 갱신 함수 호출

    })
    .catch(error => {
        console.error("❌ 챗봇 응답 오류:", error);
    });

    document.getElementById("user-message").value = "";
}


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
        const loadingMessage = lastBotResponse.querySelector("#bot-loading-message");
        if (loadingMessage) {
            loadingMessage.textContent = responseMessage;  // 로딩 메시지를 실제 응답으로 교체
        }
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
