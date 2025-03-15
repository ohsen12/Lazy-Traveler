const updatePassword = async () => {
    const newPassword = document.getElementById("new-password").value;
    const confirmPassword = document.getElementById("confirm-password").value;

    // 비밀번호 확인
    if (newPassword !== confirmPassword) {
        alert("새 비밀번호와 확인 비밀번호가 일치하지 않습니다.");
        return;
    }

    try {
        const response = await axios.post("http://127.0.0.1:8000/accounts/update_password/", {
            new_password: newPassword
        });

        console.log("비밀번호 변경 성공:", response.data);
        alert("비밀번호가 성공적으로 변경되었습니다.");
    } catch (error) {
        console.error("비밀번호 변경 실패:", error.response?.data || error);
        alert("비밀번호 변경 실패.");
    }
};

document.getElementById("update-password-form").addEventListener("submit", (event) => {
    event.preventDefault();
    updatePassword();
});


