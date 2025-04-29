# **Tài liệu mô tả API TikTok & YouTube Downloader**

## **1. Giới thiệu**
API này cho phép tải xuống âm thanh (MP3) từ video TikTok và YouTube. Nó hỗ trợ nhiều định dạng URL khác nhau, bao gồm:
- **TikTok**: Video, ảnh (photo), và các URL rút gọn (`vm.tiktok.com`).
- **YouTube**: Video thông thường (`youtube.com`, `youtu.be`) và YouTube Music.

## **2. Công nghệ sử dụng**
- **Backend**: FastAPI (Python) - Framework hiệu suất cao để xây dựng API.
- **Thư viện chính**:
  - `yt-dlp`: Tải video/audio từ YouTube và TikTok.
  - `requests`: Gửi HTTP requests để lấy dữ liệu từ API TikTok.
  - `uvicorn`: ASGI server để chạy FastAPI.
- **Xử lý file**:
  - Tự động dọn dẹp file cũ sau 24 giờ.
  - Sử dụng `FFmpeg` (thông qua `yt-dlp`) để chuyển đổi sang MP3.
- **Bảo mật**:
  - CORS mở rộng (`allow_origins=["*"]`) để tích hợp với frontend.
  - Kiểm tra URL hợp lệ trước khi tải.

---

## **3. Tính năng chính**
### **3.1. Tải MP3 từ URL**
- **Endpoint**: `GET /download/?url=<URL>`
- **Hỗ trợ**:
  - TikTok (video/photo)
  - YouTube (video/music)
- **Ví dụ**:
  ```bash
  curl "http://localhost:8000/download/?url=https://www.tiktok.com/@user/video/123456789"
  ```
  → Trả về file MP3 với tên tự động (ví dụ: `user_123456789.mp3`).

### **3.2. Kiểm tra URL (Debug)**
- **Endpoint**: `GET /check-url/?url=<URL>`
- **Trả về thông tin phân tích URL**:
  ```json
  {
    "url": "https://www.tiktok.com/@user/video/123456789",
    "url_name": "user_123456789",
    "tiktok_id": "123456789",
    "is_tiktok": true,
    "is_tiktok_photo": false
  }
  ```

### **3.3. Tự động dọn dẹp file cũ**
- Xóa các file MP3 cũ hơn **24 giờ** khi khởi động server hoặc gọi `/cleanup/`.

---

## **4. Cách thức hoạt động**
### **4.1. Quy trình tải TikTok**
1. **Trích xuất ID** từ URL (ví dụ: `123456789` từ `/video/123456789`).
2. **3 phương pháp tải**:
   - **API TikTok**: Gọi API không chính thức để lấy link âm thanh.
   - **yt-dlp**: Tải trực tiếp bằng `yt-dlp` nếu API thất bại.
   - **TikTok Scraper**: Dùng CLI `tiktok-scraper` nếu có sẵn.

### **4.2. Quy trình tải YouTube**
- Sử dụng `yt-dlp` để tải và chuyển đổi thành MP3.
- Tự động đặt tên file dựa trên tiêu đề video.

### **4.3. Xử lý lỗi**
- **URL không hợp lệ**: Trả về `400 Bad Request`.
- **Lỗi tải**: Trả về `500 Internal Server Error` với thông báo chi tiết.
- **File không tồn tại**: Xóa file tạm và thông báo lỗi.

---

## **5. Cài đặt & Chạy**
### **5.1. Yêu cầu**
- Python 3.7+
- Các thư viện:  
  ```bash
  pip install fastapi uvicorn yt-dlp requests
  ```
- **FFmpeg** (cần thiết để chuyển đổi sang MP3):
  ```bash
  # Ubuntu/Debian
  sudo apt install ffmpeg

  # macOS (Homebrew)
  brew install ffmpeg
  ```

### **5.2. Khởi động server**
```bash
python main.py
```
→ Server chạy tại `http://localhost:8000`.

---

## **6. Giấy phép (License)**
- **MIT License** (mặc định) hoặc **Apache 2.0**.
- Cho phép sử dụng tự do, chỉ yêu cầu giữ lại thông báo bản quyền.

---

## **7. Hạn chế & Hướng phát triển**
### **Hạn chế**
- TikTok có thể chặn API động sau một thời gian.
- YouTube có thể giới hạn tải với một số video.

### **Cải tiến tương lai**
- Thêm hỗ trợ **Instagram Reels**.
- Tích hợp **Redis** để caching URL.
- Tối ưu tốc độ tải bằng đa luồng.

---

## **8. Tài liệu tham khảo**
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp)
- [TikTok API Unofficial Docs](https://github.com/Evil0ctal/TikTokDownloader_PyWebIO)

---

**📌 Lưu ý**: API này chỉ dùng cho mục đích học tập. Tuân thủ Điều khoản dịch vụ của TikTok/YouTube khi sử dụng.