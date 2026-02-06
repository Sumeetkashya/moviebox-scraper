import os, requests, json, time, base64, pickle, random
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from instagrapi import Client
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, vfx

# --- 🛠️ FIX FOR PIL ERROR ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ----------------------------

# --- CONFIGURATION ---
PENDING_FOLDER_ID = "1q0fYCs6yAZG6dmlUH6ql4M5eLLbUPa2V"
MOVIEBOX_URL = "https://moviebox.ph/share/post?id=6469190882641300568&package_name=com.community.oneroom"

# Instagram Credentials
INSTA_USER = "uselesss.guys"
INSTA_PASS = "Maav5nik@me"

# --- HASHTAGS & CAPTIONS ---
HASHTAGS = """
#shorts #reels #trending #viral #movies #cinema #bollywood #hollywood 
#uselessguys #kroldit #foryou #fyp #movieclips #mustwatch 
"""

CAPTIONS = [
    "Wait for the twist! 😱",
    "Ekdum kadak scene! 🔥",
    "Ye ending miss mat karna! ✨",
    "Legendary movie moment 🎬",
    "Best scene ever? 🍿",
    "You won't believe this! 🤯"
]

def get_services():
    token_data = base64.b64decode(os.environ["YT_TOKEN_BASE64"])
    creds = pickle.loads(token_data)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds), build('youtube', 'v3', credentials=creds)

# --- 📸 INSTAGRAM FUNCTION ---
def post_to_instagram(video_path, thumbnail_path, caption):
    print("📸 Posting to Instagram Reels...")
    
    cl = Client()
    cl.request_timeout = 90  # Timeout badha diya (90s) taaki upload na atke
    
    # 1. Login Logic
    try:
        if "INSTA_SESSION" in os.environ:
            print("🔑 Loading Session from Secrets...")
            session_b64 = os.environ["INSTA_SESSION"]
            session_json = base64.b64decode(session_b64).decode()
            cl.set_settings(json.loads(session_json))
        cl.login(INSTA_USER, INSTA_PASS)
    except Exception as e:
        print(f"⚠️ Login Warning: {e}")

    # 2. Upload with Retry
    for attempt in range(1, 4):
        try:
            print(f"📤 Uploading Reel... (Attempt {attempt}/3)")
            time.sleep(5) # Thoda saans lene do bot ko
            
            cl.clip_upload(video_path, caption, thumbnail=thumbnail_path)
            print("✅ Instagram Reel Posted Successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Attempt {attempt} Failed: {e}")
            if attempt < 3:
                print("⏳ Waiting 20 seconds before retry...")
                time.sleep(20)
            else:
                print("❌ All attempts failed. Skipping Insta.")
                return False

def process_video(input_path, output_path, thumb_path):
    print("🎬 Editing Video & Generating Thumbnail...")
    try:
        clip = VideoFileClip(input_path)
        final_clip = clip.fx(vfx.speedx, 1.05)
        
        if os.path.exists("logo.png"):
            print("✅ Adding Logo...")
            logo = (ImageClip("logo.png")
                    .set_duration(final_clip.duration)
                    .resize(height=120)
                    .set_opacity(0.85)
                    .margin(right=25, top=25, opacity=0)
                    .set_pos(("right", "top")))
            final_clip = CompositeVideoClip([final_clip, logo])
        
        # --- 🛠️ THE MAGIC FIX (Pixel Format yuv420p) ---
        # Ye line sabse zaroori hai. Iske bina Insta fail ho raha tha.
        final_clip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24, 
            preset="ultrafast", 
            ffmpeg_params=['-pix_fmt', 'yuv420p'],  # <--- YE HAI WO FIX
            verbose=False, 
            logger=None
        )
        
        # Thumbnail Save (RGB Fix)
        print("🖼️ Generating Thumbnail...")
        frame = final_clip.get_frame(1.0)
        img = PIL.Image.fromarray(frame)
        img = img.convert("RGB")
        img.save(thumb_path, quality=95)
        
        clip.close()
        return True
    except Exception as e:
        print(f"❌ Editing Error: {e}")
        return False

def scrape_moviebox():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(MOVIEBOX_URL, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        data_script = soup.find('script', id='__NUXT_DATA__')
        if not data_script: return None
        
        data = json.loads(data_script.string)
        links = [item for item in data if isinstance(item, str) and item.endswith('.mp4')]
        
        if not os.path.exists("history.txt"): open("history.txt", "w").close()
        with open("history.txt", "r") as f: seen = f.read().splitlines()
        
        for link in links:
            if link not in seen: return link
        return None
    except Exception as e:
        print(f"❌ Scraping Error: {e}")
        return None

def main():
    print("🚀 Krold Mega Bot Started...")
    
    # 1. Search Video
    video_url = scrape_moviebox()
    if not video_url:
        print("💤 No new video found."); return

    # 2. Download
    print(f"📥 Downloading: {video_url}")
    raw_video = "raw_video.mp4"
    processed_video = "final_video.mp4"
    thumbnail_img = "thumb.jpg"
    
    r = requests.get(video_url, stream=True)
    with open(raw_video, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): f.write(chunk)

    # 3. Edit Video & Gen Thumbnail
    if not process_video(raw_video, processed_video, thumbnail_img):
        return

    # 4. Upload to YouTube (PRIORITY)
    print("📺 Uploading to YouTube...")
    try:
        drive, yt = get_services()
        caption_text = random.choice(CAPTIONS)
        
        body = {
            'snippet': {
                'title': f"{caption_text} #Shorts",
                'description': f"{caption_text}\n\nAutomated by Krold IT.\n{HASHTAGS}",
                'categoryId': '22'
            },
            'status': {'privacyStatus': 'public'}
        }
        media_yt = MediaFileUpload(processed_video, chunksize=-1, resumable=True)
        yt.videos().insert(part="snippet,status", body=body, media_body=media_yt).execute()
        print("✅ YouTube Done!")
        
        with open("history.txt", "a") as f: f.write(video_url + "\n")
        
    except Exception as e:
        print(f"❌ YouTube Error: {e}")

    # 5. Upload to Instagram (Fixed with Magic Pixel Format)
    insta_caption = f"{caption_text}\n.\n.\n{HASHTAGS}"
    post_to_instagram(processed_video, thumbnail_img, insta_caption)

    # 6. Google Drive Backup
    try:
        print("☁️ Backing up to Drive...")
        meta = {'name': f'Krold_Auto_{int(time.time())}.mp4', 'parents': [PENDING_FOLDER_ID]}
        media = MediaFileUpload(processed_video, mimetype='video/mp4')
        drive.files().create(body=meta, media_body=media).execute()
        print("✅ Drive Backup Done!")
    except Exception as e:
        print(f"⚠️ Drive Error: {e}")

    # Cleanup
    if os.path.exists(raw_video): os.remove(raw_video)
    if os.path.exists(processed_video): os.remove(processed_video)
    if os.path.exists(thumbnail_img): os.remove(thumbnail_img)
    print("🎉 All Platforms Updated!")

if __name__ == "__main__":
    main()
