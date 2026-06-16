"""
Management Node: Xử lý tra cứu, kiểm tra trạng thái, và hủy booking.
"""
import re
import unicodedata
from langchain_core.messages import AIMessage
from ai_agent.state import BookingState
from ai_agent.tools.db_tools import get_booking_info, get_user_bookings, cancel_booking


def _format_vnd(value: int | float | None) -> str:
    if value is None:
        return "Liên hệ"
    return f"{float(value):,.0f}₫"


def _normalize_text(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _status_label(status: str | None) -> str:
    labels = {
        "pending": "Đang chờ",
        "success": "Thành công",
        "failed": "Thất bại",
        "confirmed": "Đã xác nhận",
        "cancelled": "Đã hủy",
    }
    return labels.get((status or "").lower(), status or "Chưa cập nhật")


def _payment_status_label(status: str | None) -> str:
    labels = {
        "pending": "Chưa thanh toán",
        "success": "Đã thanh toán",
        "failed": "Thanh toán thất bại",
        "cancelled": "Đã hủy",
    }
    return labels.get((status or "").lower(), status or "Chưa thanh toán")


def _is_booking_list_request(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return any(keyword in normalized for keyword in {
        "booking cua toi",
        "dat phong cua toi",
        "don dat phong cua toi",
        "lich su dat phong",
        "lich su booking",
        "cac booking",
        "danh sach booking",
    })


def _format_booking_list(bookings: list[dict]) -> str:
    if not bookings:
        return (
            "Mình chưa thấy booking nào trong tài khoản của bạn.\n\n"
            "Bạn có thể đặt phòng ngay trong chatbot hoặc trên trang khách sạn."
        )

    paid_count = sum(1 for booking in bookings if booking.get("payment_status") == "success")
    unpaid_count = len(bookings) - paid_count
    message = (
        "**Booking của bạn**\n\n"
        f"Đã thanh toán: **{paid_count}** · Chưa thanh toán/thất bại: **{unpaid_count}**\n\n"
    )

    for index, booking in enumerate(bookings, 1):
        payment_status = _payment_status_label(booking.get("payment_status"))
        booking_status = _status_label(booking.get("status"))
        payment_method = booking.get("payment_method")
        payment_text = payment_status
        if payment_method:
            payment_text += f" ({payment_method})"

        message += (
            f"**{index}. Booking #{booking['booking_id']}**\n"
            f"Khách sạn: {booking['hotel_name']} - {booking['room_type']}\n"
            f"Check-in: {booking['check_in']} · Check-out: {booking['check_out']}\n"
            f"Số phòng: {booking['num_rooms']} · Tổng tiền: **{_format_vnd(booking['total_price'])}**\n"
            f"Trạng thái booking: **{booking_status}**\n"
            f"Thanh toán: **{payment_text}**\n"
            f"Ngày đặt: {booking['created_at']}\n\n"
        )

    message += "Bạn có thể gửi mã booking, ví dụ **#123**, nếu muốn xem kỹ một đơn cụ thể."
    return message


def management_node(state: BookingState) -> dict:
    """
    Node quản lý booking: tra cứu hoặc hủy.
    """
    last_message = state["messages"][-1].content
    user_id = state.get("user_id")

    # Thử trích xuất booking_id từ tin nhắn
    match = re.search(r'#?(\d+)', last_message)
    booking_id = int(match.group(1)) if match else state.get("lookup_booking_id")

    if not booking_id and _is_booking_list_request(last_message):
        if not user_id:
            return {
                "messages": [AIMessage(content="Bạn cần đăng nhập để mình kiểm tra danh sách booking của bạn.")]
            }

        bookings = get_user_bookings(user_id)
        return {"messages": [AIMessage(content=_format_booking_list(bookings))]}

    if not booking_id:
        # Chưa có booking_id → hỏi lại
        return {
            "messages": [AIMessage(content="Bạn vui lòng cho tôi biết **mã booking** (ví dụ: #123), hoặc gửi **booking của tôi** để xem danh sách booking trong tài khoản.")]
        }

    # Kiểm tra xem người dùng muốn hủy hay chỉ tra cứu
    cancel_keywords = ["hủy", "cancel", "huỷ", "xóa", "xoá"]
    wants_cancel = any(kw in last_message.lower() for kw in cancel_keywords)

    if wants_cancel and user_id:
        result = cancel_booking(booking_id, user_id)
        if "error" in result:
            return {"messages": [AIMessage(content=f"Không thể hủy booking: {result['error']}")]}
        return {
            "messages": [AIMessage(content=result["message"])],
            "lookup_booking_id": booking_id
        }

    # Tra cứu thông tin
    info = get_booking_info(booking_id)
    if "error" in info:
        return {"messages": [AIMessage(content=f"Không tìm thấy booking: {info['error']}")]}

    status_text = _status_label(info["status"])
    msg = (
        f"**Thông tin Booking #{info['booking_id']}**\n\n"
        f"Khách sạn: {info['hotel_name']} - {info['room_type']}\n"
        f"Thời gian: {info['check_in']} → {info['check_out']}\n"
        f"Số phòng: {info['num_rooms']}\n"
        f"Tổng tiền: **{_format_vnd(info['total_price'])}**\n"
        f"Trạng thái: **{status_text}**\n"
        f"Ngày đặt: {info['created_at']}\n"
    )

    if info.get("payment_status"):
        msg += f"Thanh toán: {info['payment_method']} - {info['payment_status']}\n"

    if info["status"] == "pending":
        msg += "\n_Bạn có muốn **hủy** booking này không?_"

    return {
        "messages": [AIMessage(content=msg)],
        "lookup_booking_id": booking_id
    }
