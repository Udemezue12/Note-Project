function togglePassword() {
  const p = document.getElementById("password");
  p.type = p.type === "password" ? "text" : "password";
}

function beginLoginSubmit() {
  const btn = document.getElementById("login-btn");
  btn.disabled = true;
  document.getElementById("login-btn-text").textContent = "Signing in…";
  document.getElementById("auth-response").style.display = "none";
}

function handleLoginResponse(event) {
  const btn = document.getElementById("login-btn");
  btn.disabled = false;
  document.getElementById("login-btn-text").textContent = "Sign In";

  const xhr = event.detail.xhr;

  if (xhr.status >= 200 && xhr.status < 300) {
    try {
      const data = JSON.parse(xhr.responseText);

      // ONLY store user info (safe)
      localStorage.setItem("mnemo_user", JSON.stringify(data.user));

      // ❌ DO NOT store access_token anymore

      showToast("Welcome back!", "success");

      window.location.replace("/dashboard.html");
    } catch (_) {
      window.location.href = "/login/";
    }
  } else {
    const resp = document.getElementById("auth-response");
    resp.style.display = "block";

    try {
      const err = JSON.parse(xhr.responseText);
      resp.textContent =
        err.detail || err.non_field_errors?.[0] || "Login failed";
    } catch (_) {
      resp.textContent = "Invalid credentials";
    }

    document
      .getElementById("login-form")
      .animate(
        [
          { transform: "translateX(-6px)" },
          { transform: "translateX(6px)" },
          { transform: "translateX(-4px)" },
          { transform: "translateX(4px)" },
          { transform: "translateX(0)" },
        ],
        { duration: 350, easing: "ease-out" },
      );
  }
}
