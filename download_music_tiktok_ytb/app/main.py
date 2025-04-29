from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
import uuid
import logging
import glob
import requests
import re
import json
import time
import subprocess
from urllib.parse import urlparse, parse_qs
import tempfile
from typing import Optional
from datetime import datetime, timedelta
import uvicorn
app = FastAPI()

# Thêm CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thư mục lưu file tạm thời
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Hàm lấy TikTok ID từ URL
def extract_tiktok_id(url):
    """Trích xuất TikTok ID từ URL"""
    # Kiểm tra dạng "/photo/123456789"
    photo_pattern = r'/photo/(\d+)'
    match = re.search(photo_pattern, url)
    if match:
        return match.group(1)
    
    # Kiểm tra dạng "/video/123456789"
    video_pattern = r'/video/(\d+)'
    match = re.search(video_pattern, url)
    if match:
        return match.group(1)
    
    # Phân tích URL để tìm ID trong query parameters
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    # Một số dạng URL TikTok sử dụng tham số item_id
    if 'item_id' in query_params:
        return query_params['item_id'][0]
    
    return None

# Hàm lấy tên từ URL
def get_name_from_url(url):
    """Lấy tên từ URL"""
    # Lấy username từ URL TikTok
    username_pattern = r'tiktok\.com/@([^/]+)'
    username_match = re.search(username_pattern, url)
    username = username_match.group(1) if username_match else None
    
    # Lấy ID từ URL
    tiktok_id = extract_tiktok_id(url)
    
    if username and tiktok_id:
        return f"{username}_{tiktok_id}"
    elif tiktok_id:
        return f"tiktok_{tiktok_id}"
    
    # Nếu URL là YouTube
    if 'youtube.com' in url or 'youtu.be' in url:
        video_id_pattern = r'(?:v=|youtu\.be/)([^&]+)'
        video_id_match = re.search(video_id_pattern, url)
        if video_id_match:
            return f"youtube_{video_id_match.group(1)}"
    
    # Nếu không tìm thấy bất kỳ thông tin nào
    return None

# Hàm tải nội dung từ TikTok sử dụng API động
async def download_tiktok_content(url, output_path):
    """
    Tải nội dung TikTok bằng cách truy cập API TikTok
    """
    tiktok_id = extract_tiktok_id(url)
    if not tiktok_id:
        raise ValueError("Không thể trích xuất TikTok ID từ URL")
    
    logger.info(f"Đã trích xuất TikTok ID: {tiktok_id}")
    
    # Chuẩn bị headers giống trình duyệt
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.tiktok.com/',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    # Phương pháp 1: Sử dụng API web không chính thức
    try:
        # Gửi yêu cầu với URL gốc để lấy cookie
        session = requests.Session()
        session.get("https://www.tiktok.com/", headers=headers)
        
        # Tạo URL API để lấy chi tiết
        api_url = f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={tiktok_id}"
        response = session.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Tìm URL âm thanh
            try:
                aweme_list = data.get('aweme_list', [])
                if aweme_list:
                    item = aweme_list[0]
                    music_info = item.get('music', {})
                    audio_url = music_info.get('play_url', {}).get('url_list', [])
                    
                    if audio_url and len(audio_url) > 0:
                        # Tải âm thanh
                        audio_response = session.get(audio_url[0], headers=headers)
                        if audio_response.status_code == 200:
                            with open(output_path, 'wb') as f:
                                f.write(audio_response.content)
                            return True
            except Exception as e:
                logger.error(f"Lỗi khi xử lý dữ liệu API: {str(e)}")
    
    except Exception as e:
        logger.error(f"Lỗi khi sử dụng API TikTok: {str(e)}")
    
    # Phương pháp 2: Sử dụng yt-dlp với URL được định dạng lại
    try:
        # Thử chuyển đổi URL photo thành URL video
        video_url = url.replace('/photo/', '/video/')
        logger.info(f"Thử tải với URL đã chuyển đổi: {video_url}")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': False,
            'verbose': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            return True
    
    except Exception as e:
        logger.error(f"Lỗi khi thử với URL video thay thế: {str(e)}")
    
    # Phương pháp 3: Sử dụng tiện ích dòng lệnh tikdown hoặc tương tự
    try:
        cmd = ["tiktok-scraper", "video", url, "-d", "-o", os.path.dirname(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Tìm file đã tải
            files = glob.glob(os.path.join(os.path.dirname(output_path), "*.mp3"))
            if files:
                # Di chuyển file tới output_path
                os.rename(files[0], output_path)
                return True
    except Exception as e:
        logger.error(f"Lỗi khi sử dụng tiktok-scraper: {str(e)}")
    
    # Nếu tất cả phương pháp đều thất bại
    return False

# Hàm dọn dẹp file cũ
def cleanup_old_files(max_age_hours=24):
    """Xóa các file cũ hơn max_age_hours"""
    try:
        now = datetime.now()
        cutoff = now - timedelta(hours=max_age_hours)
        
        for item in os.listdir(DOWNLOAD_DIR):
            item_path = os.path.join(DOWNLOAD_DIR, item)
            if os.path.isfile(item_path):
                mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                if mtime < cutoff:
                    os.remove(item_path)
                    logger.info(f"Đã xóa file cũ: {item_path}")
    except Exception as e:
        logger.error(f"Lỗi khi dọn dẹp file: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Chạy khi khởi động ứng dụng"""
    cleanup_old_files()

@app.get("/download/")
async def download_content(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube or TikTok URL")
):
    """
    Tải nội dung (MP3 từ video/photo) dựa trên URL.
    
    Args:
        url (str): Link video YouTube hoặc TikTok
    Returns:
        FileResponse: File MP3
    """
    # Kiểm tra URL cơ bản
    if not url.startswith(('https://www.youtube.com', 'https://youtu.be', 
                          'https://www.tiktok.com', 'https://vm.tiktok.com', 
                          'https://music.youtube.com')):
        raise HTTPException(status_code=400, detail="URL phải từ YouTube hoặc TikTok!")

    is_tiktok = 'tiktok.com' in url
    is_tiktok_photo = is_tiktok and '/photo/' in url
    
    # Lấy tên từ URL nếu có thể
    url_name = get_name_from_url(url)
    
    # Nếu không lấy được tên từ URL, sử dụng UUID
    if not url_name:
        url_name = str(uuid.uuid4())
    
    file_path = os.path.join(DOWNLOAD_DIR, f"{url_name}.mp3")
    
    try:
        # Xử lý TikTok Photo đặc biệt
        if is_tiktok_photo:
            logger.info(f"Đang xử lý TikTok Photo URL: {url}")
            success = await download_tiktok_content(url, file_path)
            
            if not success:
                raise HTTPException(
                    status_code=400, 
                    detail="Không thể tải âm thanh từ TikTok Photo. URL không được hỗ trợ hoặc không có âm thanh."
                )
                
            # Nếu tải thành công, sử dụng tên đã xác định
            title = url_name
        else:
            # Xử lý các URL khác bằng yt-dlp
            logger.info(f"Đang tải từ: {url}")
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(DOWNLOAD_DIR, url_name),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': False,
                'verbose': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', url_name)
                
                # Tìm file đã tải
                file_pattern = os.path.join(DOWNLOAD_DIR, f"{url_name}*.mp3")
                files = glob.glob(file_pattern)
                
                if not files:
                    raise HTTPException(status_code=500, detail="Không tìm thấy file MP3 sau khi tải.")
                
                file_path = files[0]
        
        # Kiểm tra file tồn tại
        if not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail=f"File {file_path} không tồn tại.")
        
        # Đảm bảo tên file hợp lệ
        safe_title = "".join([c if c.isalnum() or c in " -_()[]" else "_" for c in title])
        filename = f"{safe_title}.mp3"
        
        # Thêm nhiệm vụ dọn dẹp để chạy sau khi response được gửi
        background_tasks.add_task(lambda: os.remove(file_path) if os.path.exists(file_path) else None)
        
        logger.info(f"Trả về file: {file_path} với tên: {filename}")
        return FileResponse(
            file_path,
            media_type="audio/mpeg",
            filename=filename
        )

    except Exception as e:
        logger.error(f"Lỗi khi tải: {str(e)}")
        if "Unsupported URL" in str(e):
            raise HTTPException(status_code=400, detail="URL không được hỗ trợ, hãy kiểm tra lại!")
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải: {str(e)}")

@app.get("/")
async def root():
    return {"message": "TikTok và YouTube Downloader API. Sử dụng /download/?url=YOUR_URL để tải nội dung."}

@app.get("/cleanup/", include_in_schema=False)
async def cleanup():
    cleanup_old_files()
    return {"message": "Đã dọn dẹp các file cũ"}

# Endpoint kiểm tra URL - hữu ích cho việc debug
@app.get("/check-url/")
async def check_url(url: str = Query(..., description="URL to check")):
    url_name = get_name_from_url(url)
    tiktok_id = extract_tiktok_id(url)
    is_tiktok = 'tiktok.com' in url
    is_tiktok_photo = is_tiktok and '/photo/' in url
    
    return {
        "url": url,
        "url_name": url_name,
        "tiktok_id": tiktok_id,
        "is_tiktok": is_tiktok,
        "is_tiktok_photo": is_tiktok_photo,
    }

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)