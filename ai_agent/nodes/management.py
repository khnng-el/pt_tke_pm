"""
Management Node: Xử lý tra cứu, kiểm tra trạng thái, và hủy booking.
"""
import os
import re
from google import genai
from langchain_core.messages import AIMessage
from ai_agent.state import BookingState
from ai_agent.prompts import MANAGEMENT_PROMPT
from ai_agent.tools.db_tools import get_booking_info, cancel_booking


def _format_vnd(value: int | float | None) -> str:
    if value is None:
        return "Liên hệ"
    return f"{float(value):,.0f}₫"


def _status_label(status: str | None) -> str:
    labels = {
        "pending": "Đang chờ",
        "success": "Thành công",
        "failed": "Thất bại",
        "confirmed": "Đã xác nhận",
        "cancelled": "Đã hủy",
    }
    return labels.get((status or "").lower(), status or "Chưa cập nhật")


def management_node(state: BookingState) -> dict:
    """
    Node quản lý booking: tra cứu hoặc hủy.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    last_message = state["messages"][-1].content
    user_id = state.get("user_id")

    # Thử trích xuất booking_id từ tin nhắn
    match = re.search(r'#?(\d+)', last_message)
    booking_id = int(match.group(1)) if match else state.get("lookup_booking_id")

    if not booking_id:
        # Chưa có booking_id → hỏi lại
        return {
            "messages": [AIMessage(content="Bạn vui lòng cho tôi biết **mã booking** (ví dụ: #123) để tôi tra cứu giúp bạn.")]
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
