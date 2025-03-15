const logout = async () => {
    // 엑세스 토큰 가져오기
    const accessToken = localStorage.getItem("access_token");
    if (!accessToken) {
        alert("로그인이 필요합니다.");
        return;
    }

    try {
        const response = await axios.post("http://127.0.0.1:8000/accounts/logout/", {}, {
            headers: {
                'Authorization': `Bearer ${accessToken}`  // 엑세스 토큰을 Authorization 헤더에 추가
            }
        });

        console.log("로그아웃 성공:", response.data);
        alert("로그아웃 되었습니다.");

        // 로그아웃 후 로컬 스토리지에서 토큰 삭제
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");

        // ✅ 로그인 페이지로 리디렉션
        window.location.href = 'http://127.0.0.1:5500/lazy_traveler/front/pages/login/login.html';
    } catch (error) {
        console.error("로그아웃 실패:", error.response?.data || error);
        alert("로그아웃 실패.");
    }
};

document.getElementById("logout-btn").addEventListener("click", logout);

