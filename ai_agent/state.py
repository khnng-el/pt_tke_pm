"""
Định nghĩa trạng thái (State) cho LangGraph Booking Assistant.
State được truyền qua mọi Node trong đồ thị và được cập nhật tại mỗi bước.
"""
from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BookingState(TypedDict):
    """Trạng thái chính của đồ thị LangGraph."""
    
    # Lịch sử tin nhắn (được tự động nối thêm nhờ add_messages)
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Ý định người dùng: "faq", "booking", "manage", "greeting"
    intent: Optional[str]
    
    # Thông tin đặt phòng (được thu thập dần qua hội thoại)
    check_in: Optional[str]
    check_out: Optional[str]
    guests: Optional[int]
    room_type: Optional[str]
    hotel_name: Optional[str]
    
    # Kết quả truy vấn DB
    suggested_rooms: Optional[List[dict]]
    pending_room_id: Optional[int]
    booking_confirmed: Optional[bool]
    
    # Kết quả đặt phòng
    booking_id: Optional[int]
    payment_url: Optional[str]
    
    # ID người dùng hiện tại (lấy từ Flask session)
    user_id: Optional[int]
    
    # Mã booking cần tra cứu / hủy
    lookup_booking_id: Optional[int]
    
    # Vị trí GPS người dùng (cho tính năng tìm khách sạn gần nhất)
    user_lat: Optional[float]
    user_lng: Optional[float]
