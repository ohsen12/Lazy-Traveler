let map, marker, infowindow, geocoder;

kakao.maps.load(() => {
    var container = document.getElementById('map');
    var options = { 
        center: new kakao.maps.LatLng(37.5704, 126.9831), // 📌 기본 위치: 종각역
        level: 3 
    };
    map = new kakao.maps.Map(container, options);
    geocoder = new kakao.maps.services.Geocoder();

    // 📌 기본 마커 (종각역)
    marker = new kakao.maps.Marker({
        position: new kakao.maps.LatLng(37.5704, 126.9831),
        map: map
    });

    // 📌 정보창 추가
    infowindow = new kakao.maps.InfoWindow({
        content: `<div style="padding:5px;">📍 종각역</div>`
    });
    infowindow.open(map, marker);

    // 🎯 마커 클릭 시 새로운 위치로 이동하고 백엔드로 전송
    kakao.maps.event.addListener(map, "click", function(event) {
        var position = event.latLng;
        marker.setPosition(position);  // 마커의 위치 변경
        getAddressFromCoords(position); // 새로운 주소 가져오기
        sendLocationToBackend(position); // 백엔드로 위치 전송
    });
});

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
                sendLocationToBackend(newPosition); // 🌟 현재 위치 백엔드로 전송
            },
            function(error) {
                alert("위치 정보를 가져올 수 없습니다. 권한을 확인하세요.");
            }
        );
    } else {
        alert("이 브라우저에서는 위치 정보가 지원되지 않습니다.");
    }
}

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

function sendLocationToBackend(coords) {
    const data = {
        latitude: coords.getLat().toFixed(6),
        longitude: coords.getLng().toFixed(6)
    };

    axios.post("http://localhost:8000/chatbot/save-location/", data)
        .then(response => {
            console.log("✅ 위치 저장 완료:", response.data);
        })
        .catch(error => {
            console.error("❌ 위치 저장 실패:", error);
        });
}


function sendMessage() {
    const userMessage = document.getElementById("user-message").value;

    if (userMessage.trim() === "") return;

    // 사용자 메시지 출력
    appendMessage(userMessage, "user-message");

    // 메시지 서버로 전송
    axios.post("http://127.0.0.1:8000/chatbot/chat/", {
        message: userMessage,
        session_id: "test1", // 세션 ID는 필요에 따라 설정하세요.
        new_session: false,  // 새로운 대화 여부를 설정할 수 있습니다.
    })
    .then(response => {
        // 챗봇 응답 출력
        const botResponse = response.data.response;
        appendMessage(botResponse, "bot-response");
    })
    .catch(error => {
        console.error("챗봇 응답 오류:", error);
    });

    // 입력란 초기화
    document.getElementById("user-message").value = "";
}

function appendMessage(message, type) {
    const messageContainer = document.createElement("div");
    messageContainer.classList.add("message", type);
    messageContainer.innerText = message;
    document.getElementById("chat-box").appendChild(messageContainer);
}