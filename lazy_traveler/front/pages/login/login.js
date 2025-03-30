document.getElementById("login-form").addEventListener("submit", async function(event) {
    event.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const messageDiv = document.getElementById('login-message');

    try {
        const response = await axios.post("https://api.lazy-traveler.store/accounts/login/", {
            username: username,
            password: password
        });


        if (response.data.access) {
            localStorage.setItem("access_token", response.data.access);
            localStorage.setItem("refresh_token", response.data.refresh);

            // ✅ 바로 페이지 이동
            goToMain();
        } else {
            messageDiv.textContent = '비밀번호가 일치하지 않습니다.';
        }
    } catch (error) {
            messageDiv.textContent = 'ID 혹은 비밀번호가 일치하지 않습니다';
    }
});

function goToMain() {
    window.location.href = 'https://lazy-traveler.store/pages/main/main.html';
}