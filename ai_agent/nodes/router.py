"""
Router Node: Phân loại ý định người dùng bằng LLM.
Đây là node đầu tiên chạy sau khi nhận tin nhắn.
"""
import re
import unicodedata
from google import genai
from langchain_core.messages import AIMessage
from ai_agent.state import BookingState
from ai_agent.prompts import ROUTER_PROMPT


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


def _is_booking_followup(state: BookingState) -> bool:
    last_message = state["messages"][-1].content or ""
    normalized = _normalize_text(last_message)
    previous_ai = _previous_ai_text(state)

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
    import os
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    # Lấy tin nhắn mới nhất của người dùng
    last_message = state["messages"][-1].content

    if _is_booking_followup(state):
        return {"intent": "booking"}

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
