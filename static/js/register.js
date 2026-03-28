document.getElementById("reg-password")?.addEventListener("input", function () {
  const val = this.value;
  const bar = document.getElementById("password-strength");
  const label = document.getElementById("password-strength-label");
  let strength = 0;
  if (val.length >= 8) strength++;
  if (/[A-Z]/.test(val)) strength++;
  if (/[0-9]/.test(val)) strength++;
  if (/[^A-Za-z0-9]/.test(val)) strength++;
  const config = [
    { color: "var(--ember)", text: "Weak", width: "25%" },
    { color: "var(--gold)", text: "Fair", width: "50%" },
    { color: "#5b7fa6", text: "Good", width: "75%" },
    { color: "var(--sage)", text: "Strong", width: "100%" },
  ];
  if (val.length === 0) {
    bar.style.width = "0";
    label.textContent = "";
    return;
  }
  const s = config[Math.max(0, strength - 1)];
  bar.style.background = s.color;
  bar.style.width = s.width;
  label.textContent = s.text;
  label.style.color = s.color;
});

// Confirm match indicator
document.getElementById("reg-confirm")?.addEventListener("input", function () {
  const pw = document.getElementById("reg-password").value;
  const el = document.getElementById("confirm-match");
  el.style.display = "block";
  if (this.value === pw) {
    el.textContent = "✓ Passwords match";
    el.style.color = "var(--sage)";
  } else {
    el.textContent = "✕ Passwords do not match";
    el.style.color = "var(--ember)";
  }
});

function beginRegister() {
  document.getElementById("register-btn").disabled = true;
  document.getElementById("register-btn-text").textContent =
    "Creating account…";
}

function handleRegisterResponse(event) {
  document.getElementById("register-btn").disabled = false;
  document.getElementById("register-btn-text").textContent = "Create Account";
  const xhr = event.detail.xhr;
  const resp = document.getElementById("auth-response");
  resp.style.display = "block";
  if (xhr.status === 201) {
    resp.style.background = "rgba(74,124,89,0.1)";
    resp.style.border = "1px solid rgba(74,124,89,0.3)";
    resp.style.color = "var(--sage)";
    resp.textContent = "✓ Account created! Check your email to verify.";
    document.getElementById("register-form").style.opacity = "0.4";
    document.getElementById("register-form").style.pointerEvents = "none";
    setTimeout(() => (window.location.href = "/login/"), 2500);
  } else {
    resp.style.background = "rgba(232,81,42,0.1)";
    resp.style.border = "1px solid rgba(232,81,42,0.3)";
    resp.style.color = "var(--ember)";
    try {
      const err = JSON.parse(xhr.responseText);
      const msgs = Object.values(err).flat();
      resp.textContent = msgs[0] || "Registration failed";
    } catch (_) {
      resp.textContent = "Registration failed. Please try again.";
    }
  }
}
