"""
Script test cho AI Booking Assistant (LangGraph).
Chạy ở terminal để hội thoại trực tiếp với Agent.
"""
# Tắt SQL log TRƯỚC KHI import bất kỳ thứ gì (config.py tạo engine với echo=True)
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

import os
import sys

# Đảm bảo import từ thư mục gốc dự án
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'chatbot_system', '.env'))

from ai_agent.graph import chat
from langchain_core.messages import HumanMessage, AIMessage


def main():
    print("=" * 60)
    print(" HaNoi Booking — AI Booking Assistant (LangGraph)")
    print("=" * 60)
    print("Gõ 'quit' hoặc 'exit' để thoát.\n")

    history = []
    user_id = 1  # Test với user_id = 1

    while True:
        try:
            question = input("Bạn: ")
        except (EOFError, KeyboardInterrupt):
            break

        if question.strip().lower() in ['quit', 'exit']:
            print("Tạm biệt! ")
            break

        if not question.strip():
            continue

        print("\n Đang xử lý...")

        try:
            # Gọi hàm chat
            answer = chat(message=question, user_id=user_id, history=history)

            # Cập nhật lịch sử
            history.append(HumanMessage(content=question))
            history.append(AIMessage(content=answer))

            print(f"\nBot: {answer}\n")
        except Exception as e:
            print(f"\n Lỗi: {e}\n")


if __name__ == "__main__":
    main()
