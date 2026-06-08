"""
Booking Node: Xử lý logic đặt phòng khách sạn.
- Thu thập thông tin (check-in, check-out, guests...)
- Truy vấn DB tìm phòng trống
- Tạo booking + sinh link thanh toán VNPay
"""
import os
import re
import json
import unicodedata
from google import genai
from langchain_core.messages import AIMessage
from ai_agent.state import BookingState
from ai_agent.prompts import BOOKING_PROMPT
from ai_agent.tools.db_tools import (
    search_available_rooms,
    create_booking_record,
    search_hotels_by_description,
    _extract_price_limit,
)
from ai_agent.tools.payment_tools import generate_payment_url


DESCRIPTION_MATCH_HINTS = [
    "tien ich", "mo ta", "phu hop", "tuong dong", "tuong tu", "goi y",
    "recommend", "khach san nao", "hotel nao", "phong co", "co ho boi",
    "khach san co", "khach san gan", "khach san o", "can khach san co",
    "muon khach san co", "noi co", "cho co",
    "gia re", "muc gia re", "re nhat", "gia tot", "tiet kiem", "binh dan",
    "duoi", "tam gia", "khoang gia", "toi da", "trieu", "vnd",
    "cheap", "budget", "low price", "affordable",
    "ho boi", "be boi", "spa", "gym", "view bien", "gan bien", "bai bien",
    "sat bien", "villa", "rieng tu", "gia dinh", "tre em", "ban cong",
    "mountain", "nui", "yen tinh", "pho co", "trung tam", "ha noi",
    "phu quoc", "ha long", "cam ranh", "da nang",
]

BEACH_MATCH_HINTS = ["gan bien", "bai bien", "sat bien", "view bien", "bien"]
BUDGET_MATCH_HINTS = [
    "gia re", "muc gia re", "re nhat", "gia tot", "tiet kiem", "binh dan",
    "cheap", "budget", "low price", "affordable",
]
ROOM_REQUEST_HINTS = ["phong", "room", "suite", "villa"]


def _normalize_text(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _human_history_text(state: BookingState) -> str:
    return "\n".join(
        msg.content for msg in state["messages"]
        if getattr(msg, "type", None) == "human"
    )


def _is_description_match_request(text: str, room_type: str | None = None,
                                  hotel_name: str | None = None) -> bool:
    if hotel_name:
        return False
    normalized = _normalize_text(" ".join([text or "", room_type or ""]))
    return any(hint in normalized for hint in DESCRIPTION_MATCH_HINTS)


def _is_beach_match_request(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return any(hint in normalized for hint in BEACH_MATCH_HINTS)


def _is_budget_match_request(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return any(hint in normalized for hint in BUDGET_MATCH_HINTS) or _extract_price_limit(text) is not None


def _is_room_request(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return any(hint in normalized for hint in ROOM_REQUEST_HINTS)


def _match_intro(description: str | None) -> str:
    wants_beach = _is_beach_match_request(description)
    wants_budget = _is_budget_match_request(description)
    wants_room = _is_room_request(description)
    price_limit = _extract_price_limit(description)
    target = "phòng" if wants_room or wants_budget else "khách sạn"

    if wants_beach and price_limit:
        return f"Tôi sẽ gợi ý cho bạn những phòng gần biển trong mức giá {_format_vnd(price_limit)}/ night."
    if price_limit:
        return f"Tôi sẽ gợi ý cho bạn những phòng trong mức giá {_format_vnd(price_limit)}/ night."
    if wants_beach and wants_budget:
        return f"Tôi sẽ gợi ý cho bạn những {target} gần biển có mức giá rẻ phù hợp."
    if wants_beach:
        return f"Tôi sẽ gợi ý cho bạn những {target} gần biển phù hợp."
    if wants_budget:
        return "Tôi sẽ gợi ý cho bạn những phòng có mức giá rẻ phù hợp."
    return ""


def _format_hotel_matches(
    matches: list[dict],
    has_dates: bool,
    description: str | None = None,
) -> str:
    wants_room = _is_room_request(description) or _is_budget_match_request(description)
    title = "Gợi ý phòng phù hợp" if wants_room else "Gợi ý khách sạn phù hợp"
    if has_dates:
        title = "Gợi ý phòng còn trống phù hợp" if wants_room else "Gợi ý khách sạn còn phòng phù hợp"

    message = f"**{title}**\n\n"
    intro = _match_intro(description)
    if intro:
        message += f"{intro}\n\n"
    if any(hotel.get("distance_km") is not None for hotel in matches):
        message += "Danh sách được sắp xếp từ gần đến xa theo vị trí của bạn.\n\n"
    elif _is_budget_match_request(description):
        message += "Danh sách được ưu tiên theo mức giá thấp trước.\n\n"

    for index, hotel in enumerate(matches[:5], 1):
        price_text = f"{_format_vnd(hotel['min_price'])}/ night" if hotel["min_price"] else "liên hệ"
        rating_text = hotel["rating"] if hotel["rating"] else "N/A"
        location = _short_location(hotel["address"])

        message += (
            f"**{index}. {hotel['hotel_name']}**\n"
            f"Vị trí: {location}\n"
            f"Đánh giá: {rating_text} · Giá từ: {price_text}\n"
        )
        if hotel.get("distance_km") is not None:
            message += f"Khoảng cách: {hotel['distance_km']} km từ vị trí của bạn\n"

        if hotel["rooms"]:
            message += "Phòng gợi ý:\n"
            for room_index, room in enumerate(hotel["rooms"][:3], 1):
                room_text = (
                    f"   {room_index}. {room['room_type']} — "
                    f"{_format_vnd(room['price_per_night'])}/ night"
                )
                if has_dates:
                    room_text += f" · Room ID: {room['room_id']}"
                message += f"{room_text}\n"

        message += f"[Xem chi tiết khách sạn]({hotel['hotel_url']})\n\n"

    if has_dates:
        message += "Nếu muốn đặt phòng, bạn gửi **Room ID** để mình hỏi xác nhận trước khi tạo booking."
    else:
        message += "Nếu muốn kiểm tra phòng trống/đặt phòng, bạn cho mình ngày check-in và check-out nhé."

    return message


def _short_location(address: str | None) -> str:
    parts = [part.strip() for part in (address or "").split(",") if part.strip()]
    if len(parts) >= 2:
        return ", ".join(parts[-2:])
    return address or "Đang cập nhật vị trí"


def _format_vnd(value: int | float | None) -> str:
    if value is None:
        return "Liên hệ"
    return f"{float(value):,.0f}₫"


def _last_human_text(state: BookingState) -> str:
    for msg in reversed(state["messages"]):
        if getattr(msg, "type", None) == "human":
            return msg.content or ""
    return ""


def _previous_ai_text(state: BookingState) -> str:
    for msg in reversed(state["messages"][:-1]):
        if getattr(msg, "type", None) == "ai":
            return msg.content or ""
    return ""


def _has_recent_room_suggestions(state: BookingState) -> bool:
    previous_ai = _previous_ai_text(state)
    return "Room ID" in previous_ai and (
        "Các phòng trống phù hợp" in previous_ai
        or "Gợi ý phòng" in previous_ai
        or "Gợi ý khách sạn" in previous_ai
    )


def _allow_index_room_choice(state: BookingState) -> bool:
    return "Các phòng trống phù hợp" in _previous_ai_text(state)


def _is_affirmative(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return normalized in {
        "co", "co dat", "co dat phong", "dat", "dat phong", "xac nhan",
        "dong y", "dong y dat", "dong y dat phong", "ok", "okay", "yes",
        "confirm", "toi dong y", "toi muon dat",
    }


def _is_negative(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return normalized in {
        "khong", "khong dat", "chua", "huy", "doi phong", "chon phong khac",
        "no", "cancel",
    }


def _extract_pending_room_id_from_history(state: BookingState) -> int | None:
    for msg in reversed(state["messages"][:-1]):
        if getattr(msg, "type", None) != "ai":
            continue
        content = msg.content or ""
        if "Xác nhận đặt phòng" not in content:
            continue
        match = re.search(r"Room ID:\s*(\d+)", content)
        if match:
            return int(match.group(1))
    return None


def _extract_pending_booking_from_history(state: BookingState) -> dict | None:
    for msg in reversed(state["messages"][:-1]):
        if getattr(msg, "type", None) != "ai":
            continue
        content = msg.content or ""
        if "Xác nhận đặt phòng" not in content:
            continue
        room_match = re.search(r"Room ID:\s*(\d+)", content)
        date_match = re.search(r"Thời gian:\s*(\d{4}-\d{2}-\d{2})\s*→\s*(\d{4}-\d{2}-\d{2})", content)
        if room_match and date_match:
            return {
                "room_id": int(room_match.group(1)),
                "check_in": date_match.group(1),
                "check_out": date_match.group(2),
            }
    return None


def _find_room_choice(message: str, rooms: list[dict], allow_index: bool = False) -> dict | None:
    if not rooms:
        return None

    numbers = [int(number) for number in re.findall(r"\b\d+\b", message or "")]
    visible_rooms = rooms[:5]
    if allow_index and len(numbers) == 1 and 1 <= numbers[0] <= len(visible_rooms):
        return visible_rooms[numbers[0] - 1]

    room_by_id = {int(room["room_id"]): room for room in rooms if room.get("room_id") is not None}
    for number in numbers:
        if number in room_by_id:
            return room_by_id[number]

    return None


def _format_room_confirmation(room: dict, check_in: str, check_out: str) -> str:
    message = (
        "**Xác nhận đặt phòng**\n\n"
        "Bạn đã chọn phòng sau:\n"
        f"Khách sạn: {room['hotel_name']}\n"
        f"Phòng: {room['room_type']}\n"
        f"Thời gian: {check_in} → {check_out} ({room['nights']} đêm)\n"
        f"Tổng giá dự kiến: **{_format_vnd(room['total_price'])}**\n"
    )
    if room.get("distance_km") is not None:
        message += f"Khoảng cách: {room['distance_km']} km từ vị trí của bạn\n"
    message += (
        f"Room ID: {room['room_id']}\n\n"
        "Bạn có muốn đặt phòng này không? "
        "Trả lời **Có, đặt phòng** để xác nhận hoặc **Không** để chọn phòng khác."
    )
    return message


def _extract_booking_info(state: BookingState, api_key: str) -> dict:
    """
    Dùng LLM để trích xuất thông tin đặt phòng từ toàn bộ lịch sử hội thoại.
    Trả về dict với các key: check_in, check_out, guests, room_type, hotel_name.
    """
    client = genai.Client(api_key=api_key)

    # Gom lịch sử hội thoại thành chuỗi
    history = "\n".join([
        f"{'User' if msg.type == 'human' else 'Bot'}: {msg.content}"
        for msg in state["messages"]
    ])

    extract_prompt = f"""Bạn là bộ trích xuất thông tin đặt phòng khách sạn.

HÃY ĐỌC KỸ lịch sử hội thoại bên dưới và trích xuất thông tin theo quy tắc:
1. Khi Bot HỎI về ngày check-in và User TRẢ LỜI một ngày → đó là check_in
2. Khi Bot HỎI về ngày check-out và User TRẢ LỜI một ngày → đó là check_out  
3. Ngày có thể ở dạng DD/MM/YYYY hoặc YYYY-MM-DD → luôn chuyển về YYYY-MM-DD
4. Nếu thông tin chưa được cung cấp, trả về null

Trả về JSON thuần túy (không markdown, không giải thích):
{{"check_in": "YYYY-MM-DD hoặc null", "check_out": "YYYY-MM-DD hoặc null", "guests": "số nguyên hoặc null", "room_type": "chuỗi hoặc null", "hotel_name": "chuỗi hoặc null"}}

Lịch sử hội thoại:
{history}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=extract_prompt
    )

    # Parse JSON từ response
    text = response.text.strip()
    # Loại bỏ markdown code block nếu có
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```$', '', text)

    try:
        info = json.loads(text)
    except json.JSONDecodeError:
        info = {}

    return info


def booking_node(state: BookingState) -> dict:
    """
    Node chính xử lý luồng đặt phòng.
    """
    last_human_message = _last_human_text(state)
    pending_booking = _extract_pending_booking_from_history(state)
    if pending_booking and _is_affirmative(last_human_message):
        return {
            "check_in": pending_booking["check_in"],
            "check_out": pending_booking["check_out"],
            "pending_room_id": pending_booking["room_id"],
            "booking_confirmed": True,
        }

    if pending_booking and _is_negative(last_human_message):
        return {
            "pending_room_id": None,
            "booking_confirmed": False,
            "messages": [
                AIMessage(
                    content=(
                        "Mình chưa tạo booking cho phòng đó. "
                        "Bạn có thể chọn phòng khác trong danh sách hoặc mô tả lại nhu cầu để mình gợi ý tiếp."
                    )
                )
            ],
        }

    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    # Bước 1: Trích xuất thông tin từ hội thoại
    info = _extract_booking_info(state, api_key)
    check_in = info.get("check_in") or state.get("check_in")
    check_out = info.get("check_out") or state.get("check_out")
    guests = info.get("guests") or state.get("guests")
    room_type = info.get("room_type") or state.get("room_type")
    hotel_name = info.get("hotel_name") or state.get("hotel_name")
    user_description = _human_history_text(state)
    user_lat = state.get("user_lat")
    user_lng = state.get("user_lng")
    pending_room_id = _extract_pending_room_id_from_history(state)
    price_limit = _extract_price_limit(user_description)

    updates = {
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests,
        "room_type": room_type,
        "hotel_name": hotel_name,
        "pending_room_id": None,
        "booking_confirmed": False,
    }

    if pending_room_id and _is_affirmative(last_human_message):
        updates["pending_room_id"] = pending_room_id
        updates["booking_confirmed"] = True
        return updates

    if pending_room_id and _is_negative(last_human_message):
        updates["messages"] = [
            AIMessage(
                content=(
                    "Mình chưa tạo booking cho phòng đó. "
                    "Bạn có thể chọn phòng khác trong danh sách hoặc mô tả lại nhu cầu để mình gợi ý tiếp."
                )
            )
        ]
        return updates

    if _has_recent_room_suggestions(state) and check_in and check_out:
        rooms = search_available_rooms(
            check_in=check_in,
            check_out=check_out,
            guests=guests or 1,
            room_type=room_type,
            hotel_name=hotel_name,
            user_lat=user_lat,
            user_lng=user_lng,
            sort_by_price=_is_budget_match_request(user_description),
            max_price_per_night=price_limit,
        )
        if rooms and rooms[0].get("no_match"):
            updates["messages"] = [AIMessage(content=rooms[0]["message"])]
            return updates
        if rooms and "error" in rooms[0]:
            updates["messages"] = [AIMessage(content=f"Lỗi: {rooms[0]['error']}")]
            return updates

        chosen_room = _find_room_choice(
            last_human_message,
            rooms,
            allow_index=_allow_index_room_choice(state),
        )
        if chosen_room:
            updates["suggested_rooms"] = rooms
            updates["pending_room_id"] = int(chosen_room["room_id"])
            updates["messages"] = [
                AIMessage(content=_format_room_confirmation(chosen_room, check_in, check_out))
            ]
            return updates

    # Nếu người dùng đang mô tả tiện ích/vị trí/phong cách phòng, ưu tiên gợi ý
    # khách sạn giống mô tả nhất dựa trên dữ liệu thật trong DB.
    if (
        _is_description_match_request(user_description, room_type, hotel_name)
        and not (check_in and check_out and _is_budget_match_request(user_description))
    ):
        matches = search_hotels_by_description(
            description=user_description,
            check_in=check_in,
            check_out=check_out,
            guests=guests or 1,
            limit=5,
            user_lat=user_lat,
            user_lng=user_lng,
        )
        if matches and matches[0].get("no_match"):
            updates["messages"] = [AIMessage(content=matches[0]["message"])]
            return updates
        if matches and "error" in matches[0]:
            updates["messages"] = [AIMessage(content=f"Lỗi: {matches[0]['error']}")]
            return updates

        updates["messages"] = [
            AIMessage(
                content=_format_hotel_matches(
                    matches,
                    bool(check_in and check_out),
                    description=user_description,
                )
            )
        ]
        return updates

    # Bước 2: Kiểm tra đủ thông tin tối thiểu (check_in + check_out) chưa
    if not check_in or not check_out:
        # Chưa đủ → gọi LLM hỏi lại
        prompt = BOOKING_PROMPT.format(
            check_in=check_in or "chưa có",
            check_out=check_out or "chưa có",
            guests=guests or "chưa có",
            room_type=room_type or "chưa có",
            hotel_name=hotel_name or "chưa có"
        )
        history = "\n".join([f"{'User' if m.type == 'human' else 'Bot'}: {m.content}" for m in state["messages"]])
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{prompt}\n\nLịch sử:\n{history}"
        )
        updates["messages"] = [AIMessage(content=response.text)]
        return updates

    # Bước 3: Đủ thông tin → Tìm phòng trống
    rooms = search_available_rooms(
        check_in=check_in,
        check_out=check_out,
        guests=guests or 1,
        room_type=room_type,
        hotel_name=hotel_name,
        user_lat=user_lat,
        user_lng=user_lng,
        sort_by_price=_is_budget_match_request(user_description),
        max_price_per_night=price_limit,
    )

    if rooms and rooms[0].get("no_match"):
        updates["messages"] = [AIMessage(content=rooms[0]["message"])]
        return updates

    if rooms and "error" in rooms[0]:
        updates["messages"] = [AIMessage(content=f"Lỗi: {rooms[0]['error']}")]
        return updates

    updates["suggested_rooms"] = rooms

    if _has_recent_room_suggestions(state):
        chosen_room = _find_room_choice(
            last_human_message,
            rooms,
            allow_index=_allow_index_room_choice(state),
        )
        if chosen_room:
            updates["pending_room_id"] = int(chosen_room["room_id"])
            updates["messages"] = [
                AIMessage(content=_format_room_confirmation(chosen_room, check_in, check_out))
            ]
            return updates

    # Bước 4: Hiển thị danh sách phòng cho khách
    rooms_text = "**Các phòng trống phù hợp**\n\n"
    if any(room.get("distance_km") is not None for room in rooms):
        rooms_text += "Danh sách được sắp xếp từ gần đến xa theo vị trí của bạn.\n\n"
    elif _is_budget_match_request(user_description):
        rooms_text += "Danh sách được ưu tiên theo mức giá thấp trước.\n\n"

    for i, r in enumerate(rooms[:5], 1):  # Giới hạn 5 kết quả
        services = ", ".join(r["services"]) if r["services"] else "Không có"
        rooms_text += (
            f"**{i}. {r['hotel_name']}** - {r['room_type']}\n"
            f"   Vị trí: {r['hotel_address']}\n"
            f"   Đánh giá: {r['hotel_rating'] or 'N/A'} · "
            f"Tổng giá: **{_format_vnd(r['total_price'])}** cho {r['nights']} đêm\n"
            f"   Dịch vụ: {services}\n"
        )
        if r.get("distance_km") is not None:
            rooms_text += f"   Khoảng cách: {r['distance_km']} km từ vị trí của bạn\n"
        rooms_text += f"   Còn {r['available_rooms']} phòng trống · Room ID: {r['room_id']}\n\n"
    rooms_text += (
        "Bạn muốn xem phòng nào? Hãy cho tôi biết **Room ID** hoặc **số thứ tự**. "
        "Mình sẽ hỏi xác nhận trước khi tạo booking."
    )

    updates["messages"] = [AIMessage(content=rooms_text)]
    return updates


def confirm_booking_node(state: BookingState) -> dict:
    """
    Node xác nhận và tạo booking khi người dùng chọn phòng.
    Được gọi khi đã có suggested_rooms và người dùng xác nhận.
    """
    user_id = state.get("user_id")
    if not user_id:
        return {"messages": [AIMessage(content="Bạn cần đăng nhập để đặt phòng.")]}

    if not state.get("booking_confirmed"):
        return {"messages": [AIMessage(content="Mình chưa nhận được xác nhận đặt phòng từ bạn.")]}

    room_id = state.get("pending_room_id")
    if not room_id:
        return {"messages": [AIMessage(content="Mình chưa thấy phòng bạn muốn đặt. Bạn vui lòng chọn phòng trước nhé.")]}

    check_in = state["check_in"]
    check_out = state["check_out"]

    # Tạo booking
    result = create_booking_record(
        user_id=user_id,
        room_id=room_id,
        check_in=check_in,
        check_out=check_out
    )

    if "error" in result:
        return {"messages": [AIMessage(content=f"Lỗi: {result['error']}")]}

    # Sinh link thanh toán VNPay
    payment_url = generate_payment_url(
        booking_id=result["booking_id"],
        amount=int(result["total_price"])
    )

    msg = (
        f"**Đặt phòng thành công**\n\n"
        f"Mã booking: **#{result['booking_id']}**\n"
        f"Khách sạn: {result['hotel_name']} - {result['room_type']}\n"
        f"Thời gian: {result['check_in']} → {result['check_out']} ({result['nights']} đêm)\n"
        f"Tổng tiền: **{_format_vnd(result['total_price'])}**\n\n"
        f"[Thanh toán qua VNPay]({payment_url})\n\n"
        f"Vui lòng thanh toán trong vòng 15 phút để giữ phòng."
    )

    return {
        "messages": [AIMessage(content=msg)],
        "booking_id": result["booking_id"],
        "payment_url": payment_url,
        "suggested_rooms": None,
        "pending_room_id": None,
        "booking_confirmed": False,
    }
