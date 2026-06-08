"""
Nearby Node: Tìm khách sạn gần nhất dựa trên vị trí GPS của người dùng.
"""
import os
import re
import json
from google import genai
from langchain_core.messages import AIMessage
from ai_agent.state import BookingState
from ai_agent.tools.location_tools import find_nearest_hotels


def _format_vnd(value: int | float | None) -> str:
    if value is None:
        return "Liên hệ"
    return f"{float(value):,.0f}₫"


def nearby_node(state: BookingState) -> dict:
    """
    Node xử lý tìm khách sạn gần nhất.
    Bước 1: Trích xuất tọa độ từ tin nhắn (hoặc hỏi lại nếu chưa có).
    Bước 2: Gọi tool tìm 3 khách sạn gần nhất.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    last_message = state["messages"][-1].content
    user_lat = state.get("user_lat")
    user_lng = state.get("user_lng")

    # Thử trích xuất tọa độ từ tin nhắn bằng LLM
    if not user_lat or not user_lng:
        extract_prompt = f"""Tin nhắn người dùng: "{last_message}"

Hãy trích xuất tọa độ GPS (latitude, longitude) từ tin nhắn trên.
Trả về JSON thuần túy: {{"lat": <số>, "lng": <số>}}
Nếu không tìm thấy tọa độ, trả về: {{"lat": null, "lng": null}}
Không giải thích, chỉ trả JSON."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=extract_prompt
        )

        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        try:
            coords = json.loads(text)
            user_lat = coords.get("lat")
            user_lng = coords.get("lng")
        except json.JSONDecodeError:
            pass

    # Nếu vẫn chưa có tọa độ → hỏi lại
    if not user_lat or not user_lng:
        msg = (
            "**Tìm khách sạn gần bạn**\n\n"
            "Tôi cần biết vị trí của bạn để gợi ý chính xác hơn.\n\n"
            "Bạn có thể cung cấp tọa độ theo một trong các cách sau:\n"
            "1. Nhập tọa độ: `21.0285, 105.8542` (vĩ độ, kinh độ)\n"
            "2. Cho biết tên thành phố hoặc khu vực bạn đang ở\n\n"
            "_Mẹo: Mở Google Maps, nhấn giữ vào vị trí rồi copy tọa độ._"
        )
        return {"messages": [AIMessage(content=msg)]}

    # Tìm 3 khách sạn gần nhất
    results = find_nearest_hotels(user_lat, user_lng, top_n=3)

    if results and "error" in results[0]:
        return {"messages": [AIMessage(content=f"Lỗi: {results[0]['error']}")]}

    # Format kết quả
    msg = "**3 khách sạn gần bạn nhất**\n\n"
    for i, h in enumerate(results, 1):
        price_text = f"{_format_vnd(h['min_price'])}/ night" if h['min_price'] else "Liên hệ"
        rating_text = h["rating"] if h["rating"] else "Chưa đánh giá"
        msg += (
            f"**{i}. {h['hotel_name']}**\n"
            f"Khoảng cách: {h['distance_km']} km\n"
            f"Vị trí: {h['address']}\n"
            f"Liên hệ: {h['phone']} · Đánh giá: {rating_text}\n"
            f"Giá từ: {price_text}\n"
            f"[Xem chi tiết khách sạn](/hotel/{h['hotel_id']})\n\n"
        )

    msg += "Bạn muốn đặt phòng tại khách sạn nào? Tôi sẽ hỗ trợ kiểm tra phòng trống ngay."

    return {
        "messages": [AIMessage(content=msg)],
        "user_lat": user_lat,
        "user_lng": user_lng,
    }
