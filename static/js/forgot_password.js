function beginForgot() {
    document.getElementById("forgot-btn").disabled = true;
    document.getElementById("forgot-btn-text").textContent = "Sending…";
  }

  // ✅ ADD IT HERE (before it's used)
  function extractErrorMessage(data) {
    if (!data) return "Request failed";

    // DRF standard
    if (data.detail) return data.detail;

    // Custom message
    if (data.message) return data.message;

    // Field errors (e.g. { email: ["error"] })
    if (typeof data === "object") {
      for (const key in data) {
        if (Array.isArray(data[key]) && data[key].length > 0) {
          return data[key][0]; // ✅ return first error
        }
      }
    }

    return "Something went wrong";
  }

  function handleForgotResponse(event) {
    document.getElementById("forgot-btn").disabled = false;
    document.getElementById("forgot-btn-text").textContent = "Send Reset Link";

    const xhr = event.detail.xhr;
    const resp = document.getElementById("auth-response");

    resp.style.display = "block";

    if (xhr.status === 200) {
      resp.style.cssText +=
        "background:rgba(74,124,89,0.1);border:1px solid rgba(74,124,89,0.3);color:var(--sage);";

      resp.textContent = "We’re processing your request. If the email is registered, you’ll receive a password reset link shortly. Redirecting...";

      document.getElementById("forgot-form").style.opacity = "0.4";
      document.getElementById("forgot-form").style.pointerEvents = "none";

      setTimeout(() => {
        window.location.href = "/reset_password/";
      }, 1000);
    } else {
      resp.style.cssText +=
        "background:rgba(232,81,42,0.1);border:1px solid rgba(232,81,42,0.3);color:var(--ember);";

      try {
        const data = JSON.parse(xhr.responseText);
        resp.textContent = extractErrorMessage(data);
      } catch (e) {
        resp.textContent = xhr.responseText || "Something went wrong";
      }
    }
  }