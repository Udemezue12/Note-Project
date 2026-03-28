const urlToken = new URLSearchParams(window.location.search).get("token");

const form = document.getElementById("verify-form");
const tokenInput = document.getElementById("verify-token");
const otpField = document.getElementById("verify-otp-field");
const resp = document.getElementById("auth-response");

// AUTO VERIFY IF TOKEN PRESENT
if (urlToken) {
  tokenInput.value = urlToken;
  otpField.style.display = "none";

  resp.style.display = "block";
  resp.textContent = "Verifying your email...";

  setTimeout(() => form.requestSubmit(), 300);
}

// VERIFY FLOW
function beginVerify() {
  document.getElementById("verify-btn").disabled = true;
  document.getElementById("verify-btn-text").textContent = "Verifying…";
}

function handleVerifyResponse(event) {
  const xhr = event.detail.xhr;

  document.getElementById("verify-btn").disabled = false;
  document.getElementById("verify-btn-text").textContent = "Verify Email";

  resp.style.display = "block";

  if (xhr.status === 200) {
    resp.style.cssText =
      "display:block;background:rgba(74,124,89,.1);border:1px solid rgba(74,124,89,.3);color:var(--sage);font-size:.72rem;font-family:var(--mono);padding:8px 12px;border-radius:4px;margin-bottom:12px;";
    resp.textContent = "✓ Email verified! Redirecting…";

    setTimeout(() => (window.location.href = "/dashboard/"), 1500);
  } else {
    resp.style.cssText =
      "display:block;background:rgba(232,81,42,.1);border:1px solid rgba(232,81,42,.3);color:var(--ember);font-size:.72rem;font-family:var(--mono);padding:8px 12px;border-radius:4px;margin-bottom:12px;";
    resp.textContent = "Invalid or expired verification code.";
  }
}

// MODAL CONTROL
function openResendModal() {
  document.getElementById("resend-modal").style.display = "flex";
}

function closeResendModal() {
  document.getElementById("resend-modal").style.display = "none";
}

async function submitResend() {
  const email = document.getElementById("resend-email").value.trim();
  const box = document.getElementById("resend-response");

  if (!email) {
    showModalError("Enter your email");
    return;
  }

  try {
    const res = await fetch("/api/v1/auth/resend_verification_link/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrf(),
      },
      body: JSON.stringify({ email }),
      credentials: "include",
    });

    const data = await res.json();

    showModalSuccess(data.message || "Request sent");

    setTimeout(() => {
      closeResendModal();
    }, 2000);
  } catch {
    showModalError("Network error");
  }
}
function showModalSuccess(msg) {
  const box = document.getElementById("resend-response");

  box.style.display = "block";
  box.style.cssText =
    "display:block;background:rgba(74,124,89,0.1);border:1px solid rgba(74,124,89,0.3);color:var(--sage);font-size:0.72rem;font-family:var(--mono);padding:8px 12px;border-radius:4px;margin-bottom:12px;";

  box.textContent = msg;
}

function showModalError(msg) {
  const box = document.getElementById("resend-response");

  box.style.display = "block";
  box.style.cssText =
    "display:block;background:rgba(232,81,42,0.1);border:1px solid rgba(232,81,42,0.3);color:var(--ember);font-size:0.72rem;font-family:var(--mono);padding:8px 12px;border-radius:4px;margin-bottom:12px;";

  box.textContent = msg;
}
