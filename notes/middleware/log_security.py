import logging
import re
from urllib.parse import urlparse

from django.conf import settings
from django.http import JsonResponse
from django.utils.timezone import now
from prometheus_client import Counter

from ..cache_deps import CacheDependencies
from ..crud_deps import CRUDDependencies
from ..env import ENV
from ..models import BlockedIP

logger = logging.getLogger("security")

blocked_ips_counter = Counter(
    "blocked_ips_total",
    "Total blocked IPs"
)

ALLOWED_HOSTS = set(getattr(settings, "ALLOWED_HOSTS", []))
SAFE_IPS = ["127.0.0.1", "localhost"]

REQUEST_COUNT: dict[str, list[float]] = {}

SUSPICIOUS_PATTERNS = [
    r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
    r"(union.*select)",
    r"(select.*from)",
    r"(drop.*table)",
]

BAD_PATHS = [
    "/wp-admin",
    "/wp-login.php",
    "/.env",
    "/phpmyadmin",
]


class SecurityMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_deps = CacheDependencies()
        self.crud_deps = CRUDDependencies()

    def __call__(self, request):
        ip = self.get_client_ip(request)

        if ENV != "production":
            return self.get_response(request)

        if not self.is_allowed_host(request):
            return self.handle_violation(ip, "Disallowed host", request)

        if not self.is_allowed_origin(request):
            return self.handle_violation(ip, "Disallowed origin", request)

        if self.is_blocked(ip):
            logger.warning(f"Blocked IP tried access: {ip}")
            return self.block_response()

        rate_response = self.check_rate_limit(ip, request)
        if rate_response:
            return rate_response

        if any(path in request.path.lower() for path in BAD_PATHS):
            return self.handle_violation(ip, "Bad path access", request)

        if self.is_suspicious(request):
            self.log_suspicious(ip, request)

        return self.get_response(request)

    def is_allowed_host(self, request):
        host = request.get_host().split(":")[0].lower()

        if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
            return True

        for allowed in ALLOWED_HOSTS:
            if allowed.startswith("."):
                if host == allowed[1:] or host.endswith(allowed):
                    return True
            elif host == allowed:
                return True

        return False

    def is_allowed_origin(self, request):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        origin = request.META.get("HTTP_ORIGIN", "")
        referer = request.META.get("HTTP_REFERER", "")
        source = origin or referer

        if not source:
            return False

        parsed = urlparse(source)
        host = parsed.netloc.lower()

        for allowed in ALLOWED_HOSTS:
            clean = allowed.lstrip(".").lower()

            if host == clean or host.endswith("." + clean):
                return True

        return False

    def get_client_ip(self, request):
        if getattr(settings, "USE_X_FORWARDED_HOST", False):
            x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded:
                return x_forwarded.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR")

    def is_blocked(self, ip):
        return self.crud_deps.exists(
            BlockedIP, ip_address=ip, is_active=True
        )

    def check_rate_limit(self, ip, request):
        key = f"rate:{ip}"

        if ENV == "production":
            count = self.cache_deps.increment(key, timeout=60)

            if count > 100:
                self.cache_deps.delete_from_cache(key)
                return self.handle_violation(ip, "Rate limit exceeded", request)

            self.cache_deps.set_from_cache(key, count + 1, timeout=60)
            return None

        current_time = now().timestamp()

        REQUEST_COUNT.setdefault(ip, [])
        REQUEST_COUNT[ip] = [
            t for t in REQUEST_COUNT[ip] if current_time - t < 60
        ]

        REQUEST_COUNT[ip].append(current_time)

        if len(REQUEST_COUNT) > 101:
            REQUEST_COUNT.clear()

        if len(REQUEST_COUNT[ip]) > 100:
            return self.handle_violation(ip, "Rate limit exceeded (dev)", request)

    def is_suspicious(self, request):
        data = str(request.GET) + str(request.POST)

        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, data, re.IGNORECASE):
                return True
        return False

    def log_suspicious(self, ip, request):
        logger.warning(
            f"SUSPICIOUS activity IP={ip} PATH={request.path}"
        )

    def handle_violation(self, ip, reason, request):
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        obj, created = self.crud_deps.get_or_create(
            BlockedIP,
            ip_address=ip,
            defaults={
                "reason": reason,
                "user_agent": user_agent,
                "request_path": request.path,
                "attempts": 1,
                "is_active": False,
            }
        )

        if not created:
            obj.attempts += 1
            obj.last_attempt = now()

            if obj.attempts >= 3:
                obj.is_active = True

            obj.reason = reason
            obj.request_path = request.path
            obj.user_agent = user_agent
            obj.save()

        blocked_ips_counter.inc()

        logger.warning(
            f"SECURITY EVENT IP={ip} REASON={reason} ATTEMPTS={obj.attempts}"
        )

        if obj.is_active:
            return self.block_response()

        return JsonResponse(
            {"warning": "Suspicious activity detected"},
            status=429
        )

    def block_response(self):
        return JsonResponse(
            {"error": "Access denied"},
            status=403
        )
