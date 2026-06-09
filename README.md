# Hệ Thống Đặt Phòng Và Quản Lý Khách Sạn

Ứng dụng web đặt phòng và quản lý khách sạn được xây dựng bằng Flask, SQLAlchemy và MySQL. Dự án hỗ trợ đăng ký, đăng nhập, tìm kiếm khách sạn, đặt phòng, thanh toán VNPay sandbox, quản lý booking theo vai trò và chatbot trợ lý đặt phòng tích hợp Gemini.

## Mục Lục

- [Tính Năng Chính](#tính-năng-chính)
- [Công Nghệ Sử Dụng](#công-nghệ-sử-dụng)
- [Yêu Cầu Môi Trường](#yêu-cầu-môi-trường)
- [Cài Đặt Nhanh](#cài-đặt-nhanh)
- [Cấu Hình Biến Môi Trường](#cấu-hình-biến-môi-trường)
- [Khởi Tạo Database](#khởi-tạo-database)
- [Chạy Ứng Dụng](#chạy-ứng-dụng)
- [Tài Khoản Mẫu](#tài-khoản-mẫu)
- [Chatbot AI](#chatbot-ai)
- [Thanh Toán VNPay Sandbox](#thanh-toán-vnpay-sandbox)
- [Cấu Trúc Thư Mục](#cấu-trúc-thư-mục)
- [Lỗi Thường Gặp](#lỗi-thường-gặp)

## Tính Năng Chính

### Khách hàng

- Xem danh sách khách sạn và phòng.
- Tìm kiếm khách sạn theo tên, địa điểm, ngày nhận phòng, ngày trả phòng và số khách.
- Xem chi tiết khách sạn, loại phòng, hình ảnh, dịch vụ và đánh giá.
- Đăng ký, đăng nhập, đăng xuất.
- Đặt phòng và theo dõi lịch sử booking.
- Thanh toán qua VNPay sandbox.
- Cập nhật thông tin cá nhân, đổi mật khẩu và quản lý đánh giá.
- Chat với trợ lý AI để hỏi đáp, gợi ý phòng và hỗ trợ đặt phòng.

### Chủ khách sạn

- Xem dashboard theo khách sạn.
- Theo dõi lịch sử đặt phòng.
- Xem thống kê phòng, booking và doanh thu.
- Quản lý thông tin khách sạn trong phạm vi quyền sở hữu.

### Quản trị viên

- Quản lý người dùng.
- Quản lý khách sạn.
- Xem thống kê tổng quan hệ thống.

## Công Nghệ Sử Dụng

### Backend

- Python
- Flask
- Flask-Login
- Flask-Mail
- Flask-Migrate
- Flask-SQLAlchemy
- SQLAlchemy
- PyMySQL
- Alembic

### Database

- MySQL là database mặc định.
- SQLite chỉ nên dùng để thử nghiệm cục bộ khi đặt `DB_BACKEND=sqlite`.

### Frontend

- HTML, CSS, JavaScript thuần.
- Jinja2 template.
- Font Awesome.
- Static assets nằm trong `hotelsmanagementweb/`.

### AI và thanh toán

- Google Gemini API qua `google-genai`.
- LangGraph và LangChain cho luồng chatbot.
- ChromaDB cho vector store FAQ/RAG.
- VNPay sandbox cho thanh toán demo.

## Yêu Cầu Môi Trường

Máy chạy dự án cần có:

- Python 3.10 trở lên.
- MySQL Server 8.x hoặc tương đương.
- Git.
- Trình duyệt web hiện đại.
- Tài khoản/API key Gemini nếu muốn dùng chatbot AI.
- Thông tin VNPay sandbox nếu muốn test thanh toán đầy đủ.

Kiểm tra nhanh:

```bash
python3 --version
mysql --version
git --version
```

## Cài Đặt Nhanh

Clone repo:

```bash
git clone <repository-url>
cd pt_tke_pm
```

Tạo và kích hoạt môi trường ảo:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Trên Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Cài dependency:

```bash
pip install -r requirements.txt
```

Tạo file cấu hình môi trường:

```bash
cp .env.example .env
```

Sau đó sửa `.env` theo thông tin MySQL và API key của máy bạn.

## Cấu Hình Biến Môi Trường

File `.env.example` đã có sẵn các biến cần thiết. Khi tạo `.env`, không commit file `.env` lên Git vì file này có thể chứa mật khẩu và API key.

Mẫu cấu hình tối thiểu:

```env
DB_BACKEND=mysql
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DB=hotel_management

SECRET_KEY=change-this-secret-key

MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=
MAIL_SUPPRESS_SEND=1

GEMINI_API_KEY=
APP_BASE_URL=http://127.0.0.1:5001
VNP_TMN_CODE=your_vnpay_tmn_code
VNP_HASH_SECRET=your_vnpay_hash_secret
```

Ý nghĩa các biến quan trọng:

- `DB_BACKEND`: đặt `mysql` để dùng MySQL. Đặt `sqlite` chỉ khi muốn thử nghiệm nhanh.
- `DATABASE_URL`: nếu có biến này, app sẽ ưu tiên dùng nó thay cho các biến MySQL riêng lẻ.
- `DB_AUTO_CREATE`: mặc định `0`. Nên import `setup_database.sql` để có sẵn schema và data mẫu.
- `SECRET_KEY`: khóa bảo mật session Flask.
- `MAIL_SUPPRESS_SEND`: đặt `1` để tắt gửi email trong môi trường local.
- `GEMINI_API_KEY`: cần có nếu muốn chatbot AI hoạt động.
- `APP_BASE_URL`: URL gốc của app, mặc định `http://127.0.0.1:5001`.
- `VNP_TMN_CODE`, `VNP_HASH_SECRET`: thông tin VNPay sandbox.

## Khởi Tạo Database

Đăng nhập MySQL và import file setup:

```bash
mysql -u root -p < setup_database.sql
```

Nếu bạn dùng user MySQL khác:

```bash
mysql -u YOUR_USER -p < setup_database.sql
```

File `setup_database.sql` sẽ:

- Tạo database `hotel_management` nếu chưa tồn tại.
- Tạo các bảng cần thiết.
- Nạp dữ liệu mẫu về users, hotels, rooms, services, images, bookings và payments.

Nếu bị lỗi quyền tạo database, hãy tạo database trước:

```sql
CREATE DATABASE hotel_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Sau đó import lại file SQL bằng user có đủ quyền.

## Chạy Ứng Dụng

Đảm bảo đang ở thư mục gốc dự án và đã kích hoạt `.venv`:

```bash
source .venv/bin/activate
python app.py
```

App sẽ chạy mặc định tại:

```text
http://127.0.0.1:5001
```

Port `5001` được dùng vì trên macOS port `5000` thường bị AirPlay chiếm.

## Tài Khoản Mẫu

Sau khi import `setup_database.sql`, bạn có thể đăng nhập bằng các tài khoản sau:

| Vai trò | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin123` |
| Chủ khách sạn | `owner1` | `owner123` |
| Khách hàng | `customer1` | `customer123` |

## Chatbot AI

Chatbot nằm trong module `ai_agent/` và được gọi qua API:

```text
POST /api/chat
```

Để chatbot hoạt động:

1. Điền `GEMINI_API_KEY` vào `.env`.
2. Cài dependency bằng `pip install -r requirements.txt`.
3. Chạy app bằng `python app.py`.

Nếu muốn build lại vector database cho FAQ/RAG:

```bash
python chatbot_system/extract_project_data.py
python chatbot_system/build_vector_db.py
```

Nếu không cấu hình Gemini API key, website vẫn có thể chạy, nhưng chatbot sẽ không trả lời đầy đủ.

## Thanh Toán VNPay Sandbox

Ứng dụng có route thanh toán:

```text
POST /vnpay_pay
GET /vnpay_return
```

Để test thanh toán:

1. Đăng ký thông tin VNPay sandbox.
2. Điền `VNP_TMN_CODE` và `VNP_HASH_SECRET` vào `.env`.
3. Đảm bảo `APP_BASE_URL` đúng với địa chỉ app đang chạy.
4. Tạo booking và bấm thanh toán trên giao diện.

Thông tin thẻ/ngân hàng test trên VNPay sandbox:

| Trường | Giá trị |
| --- | --- |
| Ngân hàng | `NCB` |
| Số thẻ / số tài khoản | `9704198526191432198` |
| Tên chủ thẻ | `NGUYEN VAN A` |
| Ngày phát hành | `07/15` |
| OTP | `123456` |

Khi được chuyển sang trang VNPay, chọn ngân hàng `NCB`, nhập thông tin ở bảng trên và xác nhận bằng OTP `123456`.

Nếu chưa cấu hình VNPay, app sẽ báo lỗi cấu hình thanh toán khi tạo link thanh toán.

## Cấu Trúc Thư Mục

```text
pt_tke_pm/
├── app.py                         # Flask app chính, routes, auth, booking, payment, chatbot API
├── config.py                      # Cấu hình database và SQLAlchemy session
├── models.py                      # SQLAlchemy models
├── utils.py                       # Helper cho user, booking, review, email
├── setup_database.sql             # Schema và data mẫu cho MySQL
├── requirements.txt               # Dependency Python của app chính
├── .env.example                   # Mẫu biến môi trường
├── ai_agent/
│   ├── graph.py                   # LangGraph workflow cho chatbot
│   ├── nodes/                     # Các node xử lý intent, booking, FAQ, nearby
│   └── tools/                     # Tool truy vấn DB, location, payment
├── chatbot_system/
│   ├── build_vector_db.py         # Build vector store cho FAQ/RAG
│   ├── extract_project_data.py    # Tạo dữ liệu text cho vector store
│   └── vectorstore/               # Chroma vector database
├── hotelsmanagementweb/
│   ├── pages/                     # Jinja2 templates
│   ├── css/                       # Styles
│   ├── js/                        # JavaScript frontend
│   ├── assets/                    # Ảnh, icon và static assets
│   └── database/                  # Các file SQL riêng lẻ/dữ liệu phụ
└── migrations/                    # Flask-Migrate/Alembic migrations
```

## Lệnh Hữu Ích

Dùng khi cần chạy lại app:

```bash
source .venv/bin/activate
python app.py
```

Dùng khi port `5001` đang bị chiếm:

```bash
lsof -nP -iTCP:5001 -sTCP:LISTEN
kill $(lsof -ti tcp:5001)
python app.py
```

Nếu process không dừng sau lệnh `kill`, dùng:

```bash
kill -9 $(lsof -ti tcp:5001)
python app.py
```

## Lỗi Thường Gặp

### `Address already in use`

Port `5001` đang có process khác chạy. Dùng:

```bash
kill $(lsof -ti tcp:5001)
python app.py
```

### `Database connection error`

Kiểm tra lại:

- MySQL Server đã chạy chưa.
- `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DB` trong `.env`.
- Database đã được import bằng `setup_database.sql` chưa.

Thử kết nối MySQL:

```bash
mysql -u root -p
```

### Lỗi thiếu package Python

Kích hoạt lại môi trường ảo và cài dependency:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Chatbot không trả lời

Kiểm tra:

- Đã điền `GEMINI_API_KEY` trong `.env` chưa.
- API key còn hoạt động không.
- Đã cài các package `google-genai`, `langgraph`, `langchain-*`, `chromadb` chưa.
- Nếu vừa thay đổi dữ liệu FAQ, hãy build lại vector database.

### Không gửi được email

Mặc định local đang tắt gửi email bằng:

```env
MAIL_SUPPRESS_SEND=1
```

Nếu muốn gửi email thật, cấu hình SMTP Gmail:

```env
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com
MAIL_SUPPRESS_SEND=0
```

Với Gmail, nên dùng App Password thay vì mật khẩu tài khoản chính.

## Ghi Chú Khi Push Lên Git

Nên commit:

- Source code `.py`, `.html`, `.css`, `.js`.
- `setup_database.sql`.
- `.env.example`.
- `requirements.txt`.
- Static assets cần thiết trong `hotelsmanagementweb/assets/`.

Không nên commit:

- `.env`
- `.venv/`
- `__pycache__/`
- `app.log`
- `hotel_management.db`
- `.DS_Store`

Những file trên đã nằm trong `.gitignore`.

## Đóng Góp

1. Tạo branch mới:

```bash
git checkout -b feature/ten-tinh-nang
```

2. Commit thay đổi:

```bash
git add .
git commit -m "Mo ta ngan gon thay doi"
```

3. Push branch:

```bash
git push origin feature/ten-tinh-nang
```

4. Tạo Pull Request trên GitHub/GitLab.

## License

Nếu dự án có file `LICENSE`, xem chi tiết trong file đó. Nếu chưa có, hãy bổ sung license phù hợp trước khi công khai repo.
