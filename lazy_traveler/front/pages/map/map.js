let map, marker, geocoder, infowindow;

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

function sendMessage() {
    const userMessage = document.getElementById("user-message").value;
    if (userMessage.trim() === "") return;

    appendMessage(userMessage, "user-message");

    const position = marker.getPosition();
    const requestData = {
        message: userMessage,
        latitude: position.getLat().toFixed(6),
        longitude: position.getLng().toFixed(6),
    };

    // 로컬 스토리지에서 토큰 가져오기 (예시: 'access_token')
    const token = localStorage.getItem("access_token");

    // 기존 session_id 가져오기
    let sessionId = localStorage.getItem("session_id");

    const headers = token ? {
        'Authorization': `Bearer ${token}`  // 토큰이 있을 때만 Authorization 헤더 추가
    } : {};

    // 새 세션 시작하는 경우
    const isNewSession = !sessionId;

    if (isNewSession) {
        sessionId = "";  // 새로운 session_id가 필요하므로 빈 문자열을 전달
    }

    // 요청 데이터에 session_id 포함
    requestData.session_id = sessionId;
    requestData.new_session = isNewSession;

    axios.post("http://127.0.0.1:8000/chatbot/chat/", requestData, { headers })
        .then(response => {
            const botResponse = response.data.response;
            appendMessage(botResponse, "bot-response");

            // 새로운 session_id가 생성되면 로컬 스토리지에 저장
            if (response.data.session_id) {
                localStorage.setItem("session_id", response.data.session_id);
            }
        })
        .catch(error => {
            console.error("❌ 챗봇 응답 오류:", error);
        });

    document.getElementById("user-message").value = "";
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

function refreshChat() {
    document.getElementById('chat-box').innerHTML = ''; // 채팅 내용 초기화
    console.log("챗봇 화면이 새로고침되었습니다."); // 디버깅 로그
}

function goToMypage() {
    // 마이페이지로 이동
    window.location.href = 'http://127.0.0.1:5500/lazy_traveler/front/pages/mypage/mypage.html'// mypage.html로 리다이렉트
}

// ✅ 로그아웃
function logout() {
    localStorage.removeItem("refresh_token");  // ✅ 리프레시 토큰 삭제
    localStorage.removeItem("access_token");  // ✅ 엑세스 토큰 삭제
    localStorage.removeItem("session_id");  // ✅ 세션 아이디 삭제
    alert("로그아웃 되었습니다.");
    window.location.href = "http://127.0.0.1:5500/lazy_traveler/front/pages/login/login.html";
}


// 대화내역 보여주기
function loadChatHistory() {
    console.log("대화 기록을 불러오는 중...");  // 디버깅: 로딩 시작
    axios.get("http://127.0.0.1:8000/accounts/user_history/", {
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + localStorage.getItem("access_token"),
        }
    })
    .then(response => {
        console.log("대화 기록 불러오기 성공:", response.data);  // 응답 데이터 확인
        const data = response.data;
        const historyList = document.getElementById("chat-history");
        historyList.innerHTML = ""; // 기존 목록 초기화

        // ✅ 날짜별로 대화 내역 추가
        for (let date in data) {
            console.log(`날짜: ${date}`);  // 각 날짜 출력
            let dateItem = document.createElement("li");
            dateItem.textContent = `📅 ${date}`;
            dateItem.classList.add("history-date");
            historyList.appendChild(dateItem);

            // ✅ 각 날짜의 메시지 목록 추가
            data[date].forEach(chat => {
                console.log(`메시지: ${chat.message}`);  // 각 대화 출력

                // 📌 메시지 항목 생성
                let chatItem = document.createElement("li");
                chatItem.classList.add("history-item");

                // 📌 대화 시간 추가
                let time = new Date(chat.created_at).toLocaleTimeString("ko-KR", {
                    hour: "2-digit",
                    minute: "2-digit"
                });

                // 📌 메시지와 시간 표시
                chatItem.innerHTML = `🗨 <strong>${chat.message}</strong> <span style="color:gray;">(${time})</span>`;

                // 📌 상세 보기 버튼 추가
                let detailButton = document.createElement("button");
                detailButton.textContent = "자세히";
                detailButton.classList.add("detail-btn");
                detailButton.onclick = () => showChatDetails(chat);
                chatItem.appendChild(detailButton);

                historyList.appendChild(chatItem);
            });
        }
    })
    .catch(error => {
        console.error("대화 기록 불러오기 실패:", error);
    });
}

// 📌 대화 상세 내용 보여주기 함수 (예시로 팝업창 구현)
function showChatDetails(chat) {
    alert(`Message: ${chat.message}\nResponse: ${chat.response}`);
}

// 페이지가 로드될 때 대화 기록 불러오기
window.onload = function() {
    loadChatHistory();
};
