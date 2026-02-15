from __future__ import annotations

import httpx


class TelegramSendError(Exception):
    pass


def send_message(
    *, token: str, chat_id: str, text: str, parse_mode: str | None = None, disable_preview: bool = True
) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_preview,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    with httpx.Client(timeout=10.0) as client:
        r = client.post(url, json=payload)

    try:
        data = r.json()
    except Exception:
        raise TelegramSendError(f"Non-JSON response: status={r.status_code} body={r.text[:200]}")

    if r.status_code != 200 or not data.get("ok"):
        raise TelegramSendError(f"sendMessage failed: status={r.status_code} data={data}")

    return data
