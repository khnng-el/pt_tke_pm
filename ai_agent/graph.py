"""
Định nghĩa StateGraph chính cho AI Booking Assistant.
Đây là file trung tâm nơi tất cả các Node và Edge được kết nối lại thành đồ thị.
"""
import os
import sys
from dotenv import load_dotenv

# Thêm thư mục gốc dự án vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env từ chatbot_system (chứa GEMINI_API_KEY)
env_path = os.path.join(os.path.dirname(__file__), '..', 'chatbot_system', '.env')
load_dotenv(env_path, override=not bool(os.getenv("GEMINI_API_KEY")))

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

from ai_agent.state import BookingState
from ai_agent.prompts import GREETING_RESPONSE
from ai_agent.nodes.router import router_node, route_by_intent
from ai_agent.nodes.rag_faq import rag_faq_node
from ai_agent.nodes.booking import booking_node, confirm_booking_node
from ai_agent.nodes.management import management_node
from ai_agent.nodes.nearby import nearby_node


# ===== Node bổ sung =====

def greeting_node(state: BookingState) -> dict:
    """Node chào hỏi — trả lời tĩnh, không cần gọi LLM."""
    return {"messages": [AIMessage(content=GREETING_RESPONSE)]}


def booking_router(state: BookingState) -> str:
    """
    Conditional edge SAU booking_node:
    - Nếu đã có suggested_rooms → chuyển sang confirm_booking
    - Nếu chưa → kết thúc (chờ tin nhắn tiếp theo)
    """
    if state.get("suggested_rooms"):
        return "confirm_booking"
    return END


# ===== Xây dựng đồ thị =====

def build_graph():
    """Xây dựng và compile StateGraph."""
    graph = StateGraph(BookingState)

    # Thêm các Node
    graph.add_node("router", router_node)
    graph.add_node("greeting", greeting_node)
    graph.add_node("faq", rag_faq_node)
    graph.add_node("booking", booking_node)
    graph.add_node("confirm_booking", confirm_booking_node)
    graph.add_node("manage", management_node)
    graph.add_node("nearby", nearby_node)

    # Entry point: mọi tin nhắn đều đi qua Router trước
    graph.set_entry_point("router")

    # Conditional edges từ Router → các node con
    graph.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "greeting": "greeting",
            "faq": "faq",
            "booking": "booking",
            "manage": "manage",
            "nearby": "nearby",
        }
    )

    # Edges kết thúc
    graph.add_edge("greeting", END)
    graph.add_edge("faq", END)
    graph.add_edge("manage", END)
    graph.add_edge("nearby", END)

    # Booking có 2 nhánh: tiếp tục hỏi hoặc confirm
    graph.add_conditional_edges(
        "booking",
        booking_router,
        {
            "confirm_booking": "confirm_booking",
            END: END,
        }
    )
    graph.add_edge("confirm_booking", END)

    return graph.compile()


# Biến global lưu graph đã compile
_compiled_graph = None


def get_graph():
    """Lấy graph đã compile (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def chat(message: str, user_id: int = None, history: list = None) -> str:
    """
    Hàm API chính để gọi chatbot.
    
    Args:
        message: Tin nhắn người dùng.
        user_id: ID người dùng (từ Flask session).
        history: Lịch sử tin nhắn BaseMessage (tùy chọn).
    
    Returns:
        Chuỗi text trả lời.
    """
    from langchain_core.messages import HumanMessage

    graph = get_graph()

    # Khởi tạo state
    messages = history or []
    messages.append(HumanMessage(content=message))

    state = {
        "messages": messages,
        "intent": None,
        "check_in": None,
        "check_out": None,
        "guests": None,
        "room_type": None,
        "hotel_name": None,
        "suggested_rooms": None,
        "booking_id": None,
        "payment_url": None,
        "user_id": user_id,
        "lookup_booking_id": None,
        "user_lat": None,
        "user_lng": None,
    }

    # Chạy đồ thị
    result = graph.invoke(state)

    # Lấy tin nhắn cuối cùng (AI response)
    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
    if ai_messages:
        return ai_messages[-1].content

    return "Xin lỗi, tôi không hiểu. Bạn có thể nói rõ hơn được không?"
