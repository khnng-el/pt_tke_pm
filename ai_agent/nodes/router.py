"""
Router Node: Phân loại ý định người dùng bằng LLM.
Đây là node đầu tiên chạy sau khi nhận tin nhắn.
"""
import re
import unicodedata
from google import genai
from ai_agent.state import BookingState
from ai_agent.prompts import ROUTER_PROMPT

DATE_TOKEN_PATTERN = re.compile(
    r"\b(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b"
)


def _normalize_text(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _previous_ai_text(state: BookingState) -> str:
    for msg in reversed(state["messages"][:-1]):
        if getattr(msg, "type", None) == "ai":
            return msg.content or ""
    return ""


def _contains_booking_date(text: str | None) -> bool:
    return bool(DATE_TOKEN_PATTERN.search(text or ""))


def _contains_booking_date_range(text: str | None) -> bool:
    return len(DATE_TOKEN_PATTERN.findall(text or "")) >= 2


def _asked_for_booking_dates(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return any(hint in normalized for hint in {
        "check in",
        "check out",
        "ngay check in",
        "ngay check out",
        "ngay nhan phong",
        "ngay tra phong",
        "ngay den",
        "ngay di",
    })


def _is_management_request(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return any(hint in normalized for hint in {
        "booking cua toi",
        "dat phong cua toi",
        "don dat phong cua toi",
        "kiem tra booking",
        "kiem tra dat phong",
        "kiem tra don dat phong",
        "lich su booking",
        "lich su dat phong",
        "xem booking",
        "xem dat phong",
        "huy booking",
        "huy dat phong",
        "trang thai booking",
        "trang thai dat phong",
    })


def _is_booking_followup(state: BookingState) -> bool:
    last_message = state["messages"][-1].content or ""
    normalized = _normalize_text(last_message)
    previous_ai = _previous_ai_text(state)

    if _contains_booking_date_range(last_message):
        return True

    if _asked_for_booking_dates(previous_ai) and _contains_booking_date(last_message):
        return True

    if "Xác nhận đặt phòng" in previous_ai:
        return normalized in {
            "co", "co dat", "co dat phong", "dat", "dat phong", "xac nhan",
            "dong y", "dong y dat", "dong y dat phong", "ok", "okay", "yes",
            "khong", "khong dat", "huy", "doi phong", "chon phong khac", "no",
        }

    if "Room ID" in previous_ai:
        if re.search(r"\b(room\s*id|id|ma\s*phong|chon|chọn|so|số)\b", last_message, re.I):
            return True
        if "Các phòng trống phù hợp" in previous_ai:
            return bool(re.fullmatch(r"\s*\d+\s*", last_message))

    return False


def router_node(state: BookingState) -> dict:
    """
    Gọi LLM để phân loại ý định (intent) từ tin nhắn mới nhất.
    Cập nhật state["intent"] = "booking" | "manage" | "faq" | "greeting"
    """
    # Lấy tin nhắn mới nhất của người dùng
    last_message = state["messages"][-1].content

    if _is_management_request(last_message):
        return {"intent": "manage"}

    if _is_booking_followup(state):
        return {"intent": "booking"}

    import os
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{ROUTER_PROMPT}\n\nTin nhắn người dùng: {last_message}"
    )

    intent = response.text.strip().lower()

    # Đảm bảo intent hợp lệ
    valid_intents = ["booking", "nearby", "manage", "faq", "greeting"]
    if intent not in valid_intents:
        intent = "faq"  # Mặc định nếu LLM trả lời lung tung

    return {"intent": intent}


def route_by_intent(state: BookingState) -> str:
    """
    Conditional edge: Dựa vào state["intent"] để quyết định đi node nào tiếp theo.
    """
    return state.get("intent", "faq")
