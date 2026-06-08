"""
Tool sinh link thanh toán VNPay.
Tái sử dụng logic VNPay từ app.py.
"""
import hashlib
import hmac
import os
import sys
import urllib.parse
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from config import get_db
from models import Payment

# Cấu hình VNPay Sandbox (lấy từ app.py)
VNPAY_URL = 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html'
VNP_TMN_CODE = os.getenv('VNP_TMN_CODE', 'U0DUG7RM')
VNP_HASH_SECRET = os.getenv('VNP_HASH_SECRET', 'HHY7JSVLHOCCD7MU0208SN9M56PL8FZZ')
APP_BASE_URL = os.getenv('APP_BASE_URL', 'http://127.0.0.1:5001')


def build_vnpay_query_and_hash(vnp_params: dict, secret_key: str) -> tuple[str, str]:
    """Tạo chuỗi query và hash cho VNPay."""
    sorted_params = sorted(vnp_params.items())
    query_string = urllib.parse.urlencode(sorted_params)
    hash_data = '&'.join([f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params])
    vnp_secure_hash = hmac.new(
        secret_key.encode('utf-8'),
        hash_data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    return query_string, vnp_secure_hash


def generate_payment_url(
    booking_id: int,
    amount: int,
    return_url: str | None = None,
) -> str:
    """
    Sinh URL thanh toán VNPay cho một booking.
    
    Args:
        booking_id: ID booking cần thanh toán.
        amount: Số tiền (VND).
        return_url: URL callback sau khi thanh toán. Mặc định trỏ về app Flask hiện tại.
    
    Returns:
        URL thanh toán VNPay đầy đủ.
    """
    if return_url is None:
        return_url = f"{APP_BASE_URL.rstrip('/')}/vnpay_return"

    now = datetime.now()
    txn_ref = f"{booking_id}_{now.strftime('%Y%m%d%H%M%S')}"

    vnp_params = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': VNP_TMN_CODE,
        'vnp_Amount': str(int(amount) * 100),  # VNPay yêu cầu nhân 100
        'vnp_CurrCode': 'VND',
        'vnp_TxnRef': txn_ref,
        'vnp_OrderInfo': f'Thanh toan dat phong #{booking_id}',
        'vnp_OrderType': 'billpayment',
        'vnp_Locale': 'vn',
        'vnp_ReturnUrl': return_url,
        'vnp_IpAddr': '127.0.0.1',
        'vnp_CreateDate': now.strftime('%Y%m%d%H%M%S'),
    }

    query_string, vnp_secure_hash = build_vnpay_query_and_hash(vnp_params, VNP_HASH_SECRET)
    db = get_db()
    try:
        db.query(Payment).filter_by(booking_id=booking_id).delete(synchronize_session=False)
        db.flush()
        payment = Payment(
            txn_ref=txn_ref,
            amount=int(amount),
            payment_method='vnpay',
            payment_status='pending',
            secure_hash=vnp_secure_hash,
            created_at=now,
            booking_id=booking_id,
        )
        db.add(payment)
        db.commit()
    except Exception:
        db.rollback()
        raise

    payment_url = f"{VNPAY_URL}?{query_string}&vnp_SecureHash={vnp_secure_hash}"

    return payment_url
