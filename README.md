Hướng dẫn cài đặt và vận hành hệ thống cục bộ
Để hệ thống website có thể hoạt động trơn tru trên môi trường máy tính cá nhân, cần thực hiện theo các bước thiết lập dưới đây:
1.Chuẩn bị môi trường
-Cài đặt ngôn ngữ lập trình Python phiên bản 3.x trở lên
-Mở Terminal/Command Prompt, di chuyển đến thư mục chứa mã nguồn dự án.
-(Tùy chọn) Tạo và kích hoạt môi trường để tránh xung đột thư viện: python -m venv venv

2.Cài đặt thư viện
-Để đảm bảo hệ thống hoạt động ổn định và tránh lỗi xung đột phiên bản, dự án đã trích xuất danh sách toàn bộ các thư viện cần thiế tvào tập tin requirements.txt
-Tiến hành cài đặt đồng loạt thông qua trình quản lý gói pip bằng lệnh sau: pip install -r requirements.txt

3.Khởi tạo cơ sở dữ liệu và tài khoản quản trị
-Thực thi lệnh để hệ thống tự động khởi tạo và đồng bộ các bảng vào file cơ sở dữ liệu SQLite: python manage.py migrate
-Tạo tài khoản quyền cao nhất để truy cập vào trang quản trị hệ thống: python manage.py createsuperuser

4.Khởi động máy chủ ảo và truy cập
-Chạy lệnh khởi động server của Django: python manage.py runserver
-Mở trình duyệt web và truy cập vào địa chỉ giao diện khách hàng: http://127.0.0.1:8000/
-Truy cập vào bảng điều khiển của quản trị viên tại địa chỉ: http://127.0.0.1:8000/admin/
