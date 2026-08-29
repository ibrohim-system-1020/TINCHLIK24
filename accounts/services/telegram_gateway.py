import json
import urllib.error
import urllib.request
from urllib.parse import urljoin

from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TelegramGatewayError(Exception):
    pass


class TelegramGatewayUnavailable(TelegramGatewayError):
    pass


class TelegramGatewaySendError(TelegramGatewayError):
    pass


class TelegramGatewayVerifyError(TelegramGatewayError):
    pass


def _gateway_request(path: str, payload: dict, timeout: int = 10) -> dict:
    token = getattr(settings, "TELEGRAM_GATEWAY_TOKEN", "")
    if not token:
        raise TelegramGatewayError("Telegram gateway token is not configured.")

    url = urljoin("https://gatewayapi.telegram.org/", path)
    data = json.dumps(payload).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            payload = json.loads(body)
            message = payload.get("message") or payload.get("error") or "Gateway API error"
        except Exception:
            message = "Gateway API returned an error."
        logger.error("HTTPError from Telegram gateway: %s", body if 'body' in locals() else str(exc))
        raise TelegramGatewaySendError(message)
    except (urllib.error.URLError, ValueError) as exc:
        logger.exception("Telegram gateway unreachable")
        raise TelegramGatewayUnavailable(
            "Telegram gateway is temporarily unavailable."
        ) from exc

    try:
        response_data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise TelegramGatewayError("Telegram gateway returned an invalid response.") from exc

    return response_data


def send_verification_message(phone_number: str) -> str:
    if not phone_number:
        raise TelegramGatewaySendError("Telefon raqam noto'g'ri.")

    payload = {
        "phone_number": phone_number,
        "code_length": 6,
    }

    response_data = _gateway_request("sendVerificationMessage", payload)

    request_id = response_data.get("request_id")
    if not request_id:
        request_id = response_data.get("result", {}).get("request_id")

    if not request_id:
        raise TelegramGatewaySendError("Telegram verification so'rovi yuborilmadi.")

    return request_id


def check_verification_status(request_id: str, code: str) -> bool:
    if not request_id or not code:
        return False

    payload = {
        "request_id": request_id,
        "code": code,
    }

    response_data = _gateway_request("checkVerificationStatus", payload)
    status = response_data.get("status")
    verified = response_data.get("verified")

    if isinstance(status, str):
        return status.lower() in {"verified", "success", "ok"}

    if isinstance(verified, bool):
        return verified

    result = response_data.get("result") or {}
    if isinstance(result, dict):
        status = result.get("status")
        if isinstance(status, str):
            return status.lower() in {"verified", "success", "ok"}
        if isinstance(result.get("verified"), bool):
            return result.get("verified")

    return False
