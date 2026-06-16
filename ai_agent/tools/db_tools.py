"""
Tools truy vấn cơ sở dữ liệu.
Tái sử dụng SQLAlchemy session từ config.py và models từ models.py.
"""
import sys
import os
import re
import unicodedata
import math

# Thêm thư mục gốc của dự án vào sys.path để import được models, config, utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Tắt SQL log output để không spam terminal khi chatbot chạy
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from datetime import datetime
from config import get_db
from models import Hotel, Room, Booking, Payment, Service, HotelLocation


FEATURE_ALIASES = {
    "gần biển / bãi biển": [
        "beach", "beachfront", "beach access", "oceanfront", "coastal",
        "bai bien", "sat bien", "gan bien", "bien", "bo bien", "ven bien",
    ],
    "view biển": [
        "ocean view", "sea view", "bay view", "view bien", "huong bien",
        "nhin ra bien", "nhin bien", "canh bien",
    ],
    "hồ bơi": [
        "pool", "pool access", "swimming pool", "ho boi", "be boi",
        "boi loi",
    ],
    "hồ bơi riêng": [
        "private pool", "ho boi rieng", "be boi rieng", "pool villa",
    ],
    "spa / wellness": [
        "spa", "wellness", "massage", "thu gian", "cham soc suc khoe",
    ],
    "phòng gym": [
        "gym", "fitness", "phong tap", "tap gym",
    ],
    "bữa sáng": [
        "breakfast", "breakfast included", "bua sang", "an sang",
    ],
    "dịch vụ phòng": [
        "room service", "dich vu phong", "phuc vu phong",
    ],
    "phù hợp gia đình": [
        "family", "family friendly", "kids", "children", "gia dinh",
        "tre em", "nhom dong", "nhieu nguoi",
    ],
    "villa / riêng tư": [
        "villa", "private", "privacy", "rieng tu", "biet thu",
        "khong gian rieng",
    ],
    "ban công": [
        "balcony", "ban cong",
    ],
    "trung tâm Hà Nội": [
        "hanoi", "ha noi", "hoan kiem", "old quarter", "pho co",
        "trung tam", "ho guom", "central hanoi",
    ],
    "Hạ Long / Quảng Ninh": [
        "ha long", "quang ninh", "bay", "vinh ha long",
    ],
    "Phú Quốc": [
        "phu quoc", "duong dong", "long beach", "kien giang",
    ],
    "Cam Ranh / Khánh Hòa": [
        "cam ranh", "khanh hoa", "bai dai", "airport", "san bay",
    ],
    "Đà Nẵng / Hội An": [
        "da nang", "hoi an", "marble mountains", "ngu hanh son",
    ],
    "núi / nghỉ dưỡng yên tĩnh": [
        "mountain", "nui", "yen tu", "heritage", "spiritual", "tam linh",
        "yen tinh", "quiet", "retreat", "thien nhien",
    ],
    "wifi": [
        "wifi", "wi-fi", "free wifi", "free wi-fi",
    ],
    "smart tv": [
        "smart tv", "tv",
    ],
    "minibar": [
        "minibar", "mini bar",
    ],
}

BUDGET_ALIASES = [
    "gia re", "muc gia re", "re nhat", "gia tot", "tiet kiem", "binh dan",
    "cheap", "budget", "low price", "affordable",
]

STRICT_LOCATION_FEATURES = {
    "gần biển / bãi biển",
    "view biển",
    "trung tâm Hà Nội",
    "Hạ Long / Quảng Ninh",
    "Phú Quốc",
    "Cam Ranh / Khánh Hòa",
    "Đà Nẵng / Hội An",
}

NO_DESCRIPTION_MATCH_MESSAGE = (
    "Không có khách sạn nào được mô tả như bạn nói, "
    "có thể liên hệ trực tiếp qua số hotline 0365651105."
)

NO_ROOM_MATCH_MESSAGE = (
    "Không có phòng nào đúng với mô tả của bạn. "
    "Để biết chi tiết hơn, vui lòng liên hệ hotline 0365651105."
)

STOPWORDS = {
    "toi", "minh", "can", "muon", "tim", "khach", "san", "hotel", "phong",
    "co", "va", "voi", "cho", "mot", "cac", "nhung", "nao", "giup", "goi",
    "y", "phu", "hop", "tuong", "tu", "nhat", "la", "o", "tai", "gan",
    "the", "a", "an", "and", "or", "with", "for", "room", "rooms", "stay",
}

DATE_TOKEN_PATTERN = re.compile(
    r"\b(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b"
)


def _normalize_text(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "d")
    value = value.lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _tokenize(value: str | None) -> set[str]:
    return {
        token for token in _normalize_text(value).split()
        if len(token) > 2 and token not in STOPWORDS
    }


def _matching_hotel_ids(db, hotel_name: str | None) -> list[int]:
    normalized_query = _normalize_text(hotel_name)
    query_tokens = _tokenize(hotel_name)
    if not normalized_query and not query_tokens:
        return []

    matched_ids = []
    hotels = db.query(Hotel.hotel_id, Hotel.hotel_name).all()
    for hotel_id, stored_name in hotels:
        normalized_name = _normalize_text(stored_name)
        name_tokens = _tokenize(stored_name)

        if normalized_query and (
            normalized_query in normalized_name
            or normalized_name in normalized_query
        ):
            matched_ids.append(hotel_id)
            continue

        if query_tokens and query_tokens.issubset(name_tokens):
            matched_ids.append(hotel_id)

    return matched_ids


def _detect_features(text: str | None) -> list[str]:
    normalized = _normalize_text(text)
    detected = []
    for label, aliases in FEATURE_ALIASES.items():
        if any(_normalize_text(alias) in normalized for alias in aliases):
            detected.append(label)
    return detected


def _is_budget_request(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return any(alias in normalized for alias in BUDGET_ALIASES)


def _extract_price_limit(text: str | None) -> int | None:
    if not text:
        return None

    text = DATE_TOKEN_PATTERN.sub(" ", text)
    value = unicodedata.normalize("NFD", text.lower())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d")
    value = value.replace(",", ".")

    unit_patterns = [
        (r"(\d+(?:\.\d+)?)\s*(?:trieu|tr|m)\b", 1_000_000),
        (r"(\d+(?:\.\d+)?)\s*(?:nghin|ngan|k)\b", 1_000),
    ]
    for pattern, multiplier in unit_patterns:
        match = re.search(pattern, value)
        if match:
            return int(float(match.group(1)) * multiplier)

    match = re.search(r"\b(\d{6,9})\b", re.sub(r"[.\s]", "", value))
    if match:
        return int(match.group(1))

    return None


def _distance_km(user_lat: float | None, user_lng: float | None,
                 hotel_lat: float | None, hotel_lng: float | None) -> float | None:
    if None in (user_lat, user_lng, hotel_lat, hotel_lng):
        return None

    radius_km = 6371
    lat1 = math.radians(float(user_lat))
    lon1 = math.radians(float(user_lng))
    lat2 = math.radians(float(hotel_lat))
    lon2 = math.radians(float(hotel_lng))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return round(radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


def _available_count_for_dates(db, room: Room, check_in_dt: datetime | None,
                               check_out_dt: datetime | None) -> int:
    if not check_in_dt or not check_out_dt:
        return int(room.availableRooms or 0)

    conflicting = db.query(Booking).filter(
        Booking.room_id == room.room_id,
        Booking.status != 'failed',
        Booking.check_in < check_out_dt,
        Booking.check_out > check_in_dt
    ).count()
    return max(int(room.availableRooms or 0) - conflicting, 0)


def search_hotels_by_description(description: str, check_in: str | None = None,
                                 check_out: str | None = None, guests: int = 1,
                                 limit: int = 5, user_lat: float | None = None,
                                 user_lng: float | None = None) -> list[dict]:
    """
    Gợi ý khách sạn/phòng giống mô tả người dùng nhất.

    Dữ liệu dùng để so khớp:
    - hotels.descriptions
    - address_hotel, hotel_name
    - rooms.room_type
    - services.serviceName theo từng phòng
    """
    query_text = (description or "").strip()
    if not query_text:
        return [{"error": "Bạn hãy mô tả tiện ích, vị trí hoặc kiểu phòng mong muốn."}]

    db = get_db()
    check_in_dt = None
    check_out_dt = None
    if check_in and check_out:
        try:
            check_in_dt = datetime.strptime(check_in, "%Y-%m-%d")
            check_out_dt = datetime.strptime(check_out, "%Y-%m-%d")
        except ValueError:
            return [{"error": "Định dạng ngày không hợp lệ. Vui lòng dùng YYYY-MM-DD."}]
        if check_in_dt >= check_out_dt:
            return [{"error": "Ngày check-out phải sau ngày check-in."}]

    try:
        user_lat = float(user_lat) if user_lat is not None else None
        user_lng = float(user_lng) if user_lng is not None else None
    except (TypeError, ValueError):
        user_lat = None
        user_lng = None

    requested_features = _detect_features(query_text)
    max_price_per_night = _extract_price_limit(query_text)
    budget_request = _is_budget_request(query_text) or max_price_per_night is not None
    query_tokens = _tokenize(query_text)
    hotels = db.query(Hotel).order_by(Hotel.rating.desc()).all()
    results = []

    for hotel in hotels:
        rooms = db.query(Room).filter(Room.hotel_id == hotel.hotel_id).all()
        room_summaries = []
        hotel_services = set()

        for room in rooms:
            services = db.query(Service).filter(Service.room_id == room.room_id).all()
            service_names = [service.serviceName for service in services]
            hotel_services.update(service_names)
            room_summaries.append(
                {
                    "room": room,
                    "services": service_names,
                    "text": " ".join([room.room_type or "", " ".join(service_names)]),
                }
            )

        corpus = " ".join(
            [
                hotel.hotel_name or "",
                hotel.address_hotel or "",
                hotel.descriptions or "",
                " ".join(room["text"] for room in room_summaries),
            ]
        )
        corpus_normalized = _normalize_text(corpus)
        corpus_tokens = _tokenize(corpus)

        matched_features = []
        score = 0.0
        for feature in requested_features:
            aliases = FEATURE_ALIASES[feature]
            feature_hit = any(_normalize_text(alias) in corpus_normalized for alias in aliases)
            if feature_hit:
                matched_features.append(feature)
                score += 24.0 if feature in STRICT_LOCATION_FEATURES else 12.0

        requested_locations = set(requested_features) & STRICT_LOCATION_FEATURES
        if requested_locations and not (set(matched_features) & requested_locations):
            continue

        overlap = query_tokens & corpus_tokens
        score += min(len(overlap) * 1.5, 18.0)
        if hotel.rating:
            score += float(hotel.rating) / 10.0
        if budget_request:
            score += 8.0

        if score <= 1.0:
            continue

        matched_rooms = []
        for item in room_summaries:
            room = item["room"]
            available_count = _available_count_for_dates(db, room, check_in_dt, check_out_dt)
            if available_count <= 0:
                continue
            if max_price_per_night is not None and int(room.price or 0) > max_price_per_night:
                continue

            room_features = _detect_features(item["text"])
            room_score = len(set(matched_features) & set(room_features)) * 6
            room_score += len(query_tokens & _tokenize(item["text"])) * 1.5

            matched_rooms.append(
                {
                    "room_id": room.room_id,
                    "room_type": room.room_type,
                    "price_per_night": int(room.price or 0),
                    "available_rooms": available_count,
                    "services": item["services"][:8],
                    "match_score": room_score,
                }
            )

        if max_price_per_night is not None and not matched_rooms:
            continue

        if budget_request:
            matched_rooms.sort(key=lambda room: (room["price_per_night"], -room["match_score"]))
        else:
            matched_rooms.sort(key=lambda room: (room["match_score"], -room["price_per_night"]), reverse=True)
        min_price = min((room["price_per_night"] for room in matched_rooms), default=None)

        location = db.query(HotelLocation).filter(
            HotelLocation.hotel_id == hotel.hotel_id
        ).first()
        distance = _distance_km(
            user_lat,
            user_lng,
            location.latitude if location else None,
            location.longitude if location else None,
        )

        results.append(
            {
                "hotel_id": hotel.hotel_id,
                "hotel_name": hotel.hotel_name,
                "address": hotel.address_hotel,
                "phone": hotel.tel,
                "rating": hotel.rating,
                "description": hotel.descriptions or "",
                "distance_km": distance,
                "matched_features": matched_features[:8],
                "services": sorted(hotel_services)[:12],
                "rooms": matched_rooms[:3],
                "min_price": min_price,
                "match_score": round(score, 2),
                "hotel_url": f"/hotel/{hotel.hotel_id}",
            }
        )

    if user_lat is not None and user_lng is not None:
        results.sort(key=lambda hotel: (
            hotel["distance_km"] is None,
            hotel["distance_km"] if hotel["distance_km"] is not None else float("inf"),
            hotel["min_price"] if budget_request and hotel["min_price"] is not None else 0,
            -hotel["match_score"],
            -(hotel["rating"] or 0),
        ))
    elif budget_request:
        results.sort(key=lambda hotel: (
            hotel["min_price"] is None,
            hotel["min_price"] if hotel["min_price"] is not None else float("inf"),
            -hotel["match_score"],
            -(hotel["rating"] or 0),
        ))
    else:
        results.sort(key=lambda hotel: (hotel["match_score"], hotel["rating"] or 0), reverse=True)

    if not results:
        no_match_message = NO_ROOM_MATCH_MESSAGE if max_price_per_night is not None else NO_DESCRIPTION_MATCH_MESSAGE
        return [{"no_match": True, "message": no_match_message}]

    return results[:limit]


def search_available_rooms(check_in: str, check_out: str, guests: int = 1,
                           room_type: str = None, hotel_name: str = None,
                           user_lat: float | None = None,
                           user_lng: float | None = None,
                           sort_by_price: bool = False,
                           max_price_per_night: int | None = None) -> list[dict]:
    """
    Tìm phòng trống dựa trên ngày check-in/out, số khách, loại phòng, tên khách sạn.
    Trả về danh sách dict chứa thông tin phòng.
    """
    db = get_db()
    try:
        check_in_dt = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_dt = datetime.strptime(check_out, "%Y-%m-%d")
    except ValueError:
        return [{"error": "Định dạng ngày không hợp lệ. Vui lòng dùng YYYY-MM-DD."}]

    if check_in_dt >= check_out_dt:
        return [{"error": "Ngày check-out phải sau ngày check-in."}]

    try:
        user_lat = float(user_lat) if user_lat is not None else None
        user_lng = float(user_lng) if user_lng is not None else None
    except (TypeError, ValueError):
        user_lat = None
        user_lng = None

    # Query phòng có số phòng trống > 0
    query = db.query(Room).join(Hotel).filter(Room.availableRooms > 0)

    if room_type:
        query = query.filter(Room.room_type.ilike(f"%{room_type}%"))
    if hotel_name:
        query = query.filter(Hotel.hotel_id.in_(_matching_hotel_ids(db, hotel_name)))
    if max_price_per_night is not None:
        query = query.filter(Room.price <= max_price_per_night)

    rooms = query.all()

    # Lọc bỏ các phòng đã bị booking trùng ngày
    available = []
    for room in rooms:
        conflicting = db.query(Booking).filter(
            Booking.room_id == room.room_id,
            Booking.status != 'failed',
            Booking.check_in < check_out_dt,
            Booking.check_out > check_in_dt
        ).count()

        # Nếu số booking trùng lịch ít hơn số phòng trống thì vẫn còn chỗ
        if conflicting < (room.availableRooms or 0):
            # Lấy danh sách dịch vụ
            services = db.query(Service).filter(Service.room_id == room.room_id).all()
            service_names = [s.serviceName for s in services]

            nights = (check_out_dt - check_in_dt).days
            total_price = room.price * nights
            location = db.query(HotelLocation).filter(
                HotelLocation.hotel_id == room.hotel_id
            ).first()
            distance = _distance_km(
                user_lat,
                user_lng,
                location.latitude if location else None,
                location.longitude if location else None,
            )

            available.append({
                "room_id": room.room_id,
                "room_type": room.room_type,
                "hotel_name": room.hotel.hotel_name,
                "hotel_address": room.hotel.address_hotel,
                "hotel_rating": room.hotel.rating,
                "price_per_night": room.price,
                "total_price": total_price,
                "nights": nights,
                "available_rooms": room.availableRooms - conflicting,
                "services": service_names,
                "distance_km": distance,
            })

    if not available:
        return [{"no_match": True, "message": NO_ROOM_MATCH_MESSAGE}]

    if user_lat is not None and user_lng is not None:
        available.sort(key=lambda room: (
            room["distance_km"] is None,
            room["distance_km"] if room["distance_km"] is not None else float("inf"),
            room["price_per_night"] if sort_by_price else 0,
            -(room["hotel_rating"] or 0),
            room["price_per_night"] or 0,
        ))
    elif sort_by_price:
        available.sort(key=lambda room: (room["price_per_night"] or 0, -(room["hotel_rating"] or 0)))
    else:
        available.sort(key=lambda room: (-(room["hotel_rating"] or 0), room["price_per_night"] or 0))

    return available


def create_booking_record(user_id: int, room_id: int, check_in: str,
                          check_out: str, num_rooms: int = 1) -> dict:
    """
    Tạo bản ghi Booking mới trong cơ sở dữ liệu.
    Trả về dict chứa thông tin booking đã tạo.
    """
    db = get_db()
    try:
        check_in_dt = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_dt = datetime.strptime(check_out, "%Y-%m-%d")
    except ValueError:
        return {"error": "Định dạng ngày không hợp lệ."}

    room = db.query(Room).filter(Room.room_id == room_id).first()
    if not room:
        return {"error": f"Không tìm thấy phòng với ID {room_id}."}

    if room.availableRooms is None or room.availableRooms < num_rooms:
        return {"error": "Phòng này không còn đủ chỗ."}

    nights = (check_out_dt - check_in_dt).days
    total_price = room.price * nights * num_rooms

    booking = Booking(
        user_id=user_id,
        room_id=room_id,
        check_in=check_in_dt,
        check_out=check_out_dt,
        total_price=total_price,
        num_rooms=num_rooms,
        status='pending'
    )
    db.add(booking)
    room.availableRooms -= num_rooms
    db.commit()
    db.refresh(booking)

    return {
        "booking_id": booking.booking_id,
        "room_type": room.room_type,
        "hotel_name": room.hotel.hotel_name,
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "total_price": total_price,
        "status": booking.status
    }


def get_booking_info(booking_id: int) -> dict:
    """Tra cứu thông tin booking theo ID."""
    db = get_db()
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        return {"error": f"Không tìm thấy booking với mã #{booking_id}."}

    result = {
        "booking_id": booking.booking_id,
        "room_type": booking.room.room_type,
        "hotel_name": booking.room.hotel.hotel_name,
        "check_in": booking.check_in.strftime("%Y-%m-%d"),
        "check_out": booking.check_out.strftime("%Y-%m-%d"),
        "total_price": booking.total_price,
        "num_rooms": booking.num_rooms,
        "status": booking.status,
        "created_at": booking.created_at.strftime("%Y-%m-%d %H:%M")
    }

    # Nếu có thanh toán
    if booking.payment:
        result["payment_status"] = booking.payment.payment_status
        result["payment_method"] = booking.payment.payment_method

    return result


def get_user_bookings(user_id: int, limit: int = 10) -> list[dict]:
    """Lấy danh sách booking của user, gồm trạng thái booking và thanh toán."""
    db = get_db()
    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for booking in bookings:
        payment = (
            db.query(Payment)
            .filter(Payment.booking_id == booking.booking_id)
            .order_by(Payment.created_at.desc())
            .first()
        )
        payment_status = payment.payment_status if payment and payment.payment_status else "pending"
        payment_method = payment.payment_method if payment and payment.payment_method else None

        results.append({
            "booking_id": booking.booking_id,
            "room_type": booking.room.room_type if booking.room else "Không rõ phòng",
            "hotel_name": booking.room.hotel.hotel_name if booking.room and booking.room.hotel else "Không rõ khách sạn",
            "check_in": booking.check_in.strftime("%Y-%m-%d") if booking.check_in else "",
            "check_out": booking.check_out.strftime("%Y-%m-%d") if booking.check_out else "",
            "total_price": booking.total_price,
            "num_rooms": booking.num_rooms,
            "status": booking.status,
            "payment_status": payment_status,
            "payment_method": payment_method,
            "created_at": booking.created_at.strftime("%Y-%m-%d %H:%M") if booking.created_at else "",
        })

    return results


def cancel_booking(booking_id: int, user_id: int) -> dict:
    """Hủy booking nếu trạng thái là pending và thuộc về đúng user."""
    db = get_db()
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        return {"error": f"Không tìm thấy booking với mã #{booking_id}."}

    if booking.user_id != user_id:
        return {"error": "Bạn không có quyền hủy booking này."}

    if booking.status != 'pending':
        return {"error": f"Không thể hủy booking ở trạng thái '{booking.status}'. Chỉ có thể hủy khi đang 'pending'."}

    booking.status = 'failed'
    # Trả lại phòng
    room = db.query(Room).filter(Room.room_id == booking.room_id).first()
    if room:
        room.availableRooms += booking.num_rooms
    db.commit()

    return {
        "message": f"Đã hủy thành công booking #{booking_id}.",
        "booking_id": booking_id,
        "status": "failed"
    }
