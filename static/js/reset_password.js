(function () {
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get("token");

  const otpField = document.getElementById("otp-field");
  const otpInput = document.getElementById("otp-input");
  const tokenInput = document.getElementById("token-input");

  const respBox = document.getElementById("auth-response");
  const btn = document.getElementById("reset-btn");
  const btnText = document.getElementById("reset-btn-text");

  // ===== Mode Detection =====
  if (!token) {
    tokenInput.removeAttribute("name");
  }
  if (token) {
    // Token mode
    otpField.style.display = "none";
    otpInput.value = "";
    otpInput.disabled = true;
    tokenInput.value = token;
  } else {
    // OTP mode
    tokenInput.removeAttribute("name");
  }

  // ===== Before Request =====
  window.beginReset = function (event) {
    const p1 = document.getElementById("new-password").value;
    const p2 = document.getElementById("confirm-new-password").value;

    if (p1 !== p2) {
      showError("Passwords do not match");
      event.preventDefault();
      return;
    }

    if (!token) {
      const otp = otpInput.value.trim();
      if (!otp || otp.length !== 6) {
        showError("Enter a valid 6-digit OTP");
        event.preventDefault();
        return;
      }
    }

    btn.disabled = true;
    btnText.textContent = "Resetting…";
  };

  // ===== After Request =====
  window.handleResetResponse = function (event) {
    btn.disabled = false;
    btnText.textContent = "Reset Password";

    respBox.style.display = "block";

    const xhr = event.detail.xhr;
    let data = {};

    try {
      data = JSON.parse(xhr.responseText || "{}");
    } catch (_) {}

    if (xhr.status === 200) {
      showSuccess("✓ Password reset! Redirecting to login…");
      setTimeout(() => {
        window.location.href = "/login/";
      }, 2000);
    } else {
      showError(data.error || "Reset failed. Check your token or OTP.");
    }
  };

  // ===== UI Helpers =====
  function showSuccess(msg) {
    respBox.style.cssText =
      "display:block;background:rgba(74,124,89,0.1);border:1px solid rgba(74,124,89,0.3);color:var(--sage);font-size:0.72rem;font-family:var(--mono);padding:8px 12px;border-radius:4px;margin-bottom:12px;";
    respBox.textContent = msg;
  }

  function showError(msg) {
    respBox.style.cssText =
      "display:block;background:rgba(232,81,42,0.1);border:1px solid rgba(232,81,42,0.3);color:var(--ember);font-size:0.72rem;font-family:var(--mono);padding:8px 12px;border-radius:4px;margin-bottom:12px;";
    respBox.textContent = msg;
  }
})();
