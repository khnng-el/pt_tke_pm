# Ứng Dụng Quản Lý Khách Sạn

Một ứng dụng web hiện đại và thân thiện với người dùng để quản lý đặt phòng khách sạn, giao dịch và tài khoản người dùng.

## Chạy Với MySQL

Project hiện được cấu hình ưu tiên MySQL mặc định.

### 1. Tạo file cấu hình môi trường

Tạo file `.env` từ mẫu:

```bash
cp .env.example .env
```

Sau đó sửa các biến MySQL trong `.env`:

```env
DB_BACKEND=mysql
MYSQL_USER=root
MYSQL_PASSWORD=mat_khau_mysql_cua_ban
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DB=hotel_management
```

### 2. Tạo database và import schema

```bash
mysql -u root -p < setup_database.sql
```

Nếu bạn không dùng user `root`, thay lại cho phù hợp:

```bash
mysql -u YOUR_USER -p < setup_database.sql
```

### 3. Cài dependency

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Chạy ứng dụng

```bash
source .venv/bin/activate
python app.py
```

Tài khoản mẫu sau khi import `setup_database.sql`:

- `admin / admin123`
- `owner1 / owner123`
- `customer1 / customer123`

## Tính Năng

### Bảng Điều Khiển Người Dùng
- Bảng điều khiển tương tác với thống kê và biểu đồ
- Quản lý đặt phòng thời gian thực
- Theo dõi lịch sử giao dịch
- Quản lý hồ sơ người dùng
- Hệ thống thông báo

### Quản Lý Khách Sạn
- Liệt kê và lọc khách sạn
- Theo dõi tình trạng phòng
- Quản lý đặt phòng
- Xử lý thanh toán
- Lịch sử giao dịch

### Giao Diện Người Dùng
- Thiết kế hiện đại và đáp ứng
- Điều hướng trực quan
- Thông báo thời gian thực
- Biểu đồ và thống kê tương tác
- Bố cục thân thiện với thiết bị di động

## Công Nghệ Sử Dụng

### Frontend
- HTML5
- CSS3 (với các tính năng hiện đại như Flexbox và Grid)
- JavaScript
- Font Awesome cho biểu tượng
- Font chữ Poppins

### Tính Năng Chính
- Thiết kế đáp ứng hoạt động trên mọi thiết bị
- Các thành phần UI hiện đại với hiệu ứng mượt mà
- Hiển thị dữ liệu tương tác
- Cập nhật thời gian thực
- Xác thực người dùng an toàn
- Tích hợp xử lý thanh toán

## Bắt Đầu

### Yêu Cầu
- Trình duyệt web hiện đại (Chrome, Firefox, Safari, Edge)
- Kết nối internet để tải font chữ và biểu tượng

### Cài Đặt
1. Sao chép kho lưu trữ
```bash
git clone [repository-url]
```

2. Di chuyển vào thư mục dự án
```bash
cd hotelsmanagementweb
```

3. Mở dự án trong trình soạn thảo mã nguồn ưa thích của bạn

4. Khởi chạy ứng dụng thông qua máy chủ cục bộ

## Cấu Trúc Dự Án

```
hotelsmanagementweb/
├── css/
│   └── user.css
├── assets/
│   └── image/
├── js/
└── index.html
```

## Chi Tiết Tính Năng

### Bảng Điều Khiển
- Tổng quan thống kê với các thẻ tương tác
- Trạng thái đặt phòng thời gian thực
- Theo dõi doanh thu
- Giám sát hoạt động người dùng

### Quản Lý Đặt Phòng
- Xem và quản lý đặt phòng khách sạn
- Theo dõi trạng thái đặt phòng
- Xử lý thanh toán
- Tạo báo cáo đặt phòng

### Hồ Sơ Người Dùng
- Quản lý thông tin cá nhân
- Lịch sử đặt phòng
- Lịch sử thanh toán
- Cài đặt tài khoản

### Thông Báo
- Hệ thống thông báo thời gian thực
- Cập nhật đặt phòng
- Xác nhận thanh toán
- Cảnh báo hệ thống

## Đóng Góp

1. Fork kho lưu trữ
2. Tạo nhánh tính năng của bạn (`git checkout -b feature/TínhNăngMới`)
3. Commit các thay đổi của bạn (`git commit -m 'Thêm một Tính Năng Mới'`)
4. Đẩy lên nhánh (`git push origin feature/TínhNăngMới`)
5. Mở Pull Request

## Giấy Phép

Dự án này được cấp phép theo Giấy phép MIT - xem tệp LICENSE để biết thêm chi tiết

## Liên Hệ

Tên của bạn - email@example.com

Liên kết dự án: [https://github.com/yourusername/hotelsmanagementweb](https://github.com/yourusername/hotelsmanagementweb)
