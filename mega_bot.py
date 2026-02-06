import os, requests, json, time, base64, pickle, random
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from instagrapi import Client  # <--- Ye naya hai
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, vfx

# --- 🛠️ FIX FOR PIL ERROR ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ----------------------------

# --- CONFIGURATION ---
PENDING_FOLDER_ID = "1q0fYCs6yAZG6dmlUH6ql4M5eLLbUPa2V"
MOVIEBOX_URL = "https://moviebox.ph/share/post?id=6469190882641300568&package_name=com.community.oneroom"

# Instagram Credentials (Backup ke liye)
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

# --- 📸 NEW: INSTAGRAM FUNCTION ---
def post_to_instagram(video_path, caption):
    print("📸 Posting to Instagram Reels...")
    try:
        cl = Client()
        
        # 1. GitHub Secret se Session uthao (Taaki Login Block na ho)
        if "INSTA_SESSION" in os.environ:
            print("🔑 Loading Session from Secrets...")
            session_b64 = os.environ["INSTA_SESSION"]
            session_json = base64.b64decode(session_b64).decode()
            cl.set_settings(json.loads(session_json))
        
        # 2. Login (Session use karega toh password ki zarurat nahi padegi usually)
        cl.login(INSTA_USER, INSTA_PASS)
        
        # 3. Upload Reel
        print("📤 Uploading Reel...")
        cl.clip_upload(video_path, caption)
        print("✅ Instagram Reel Posted Successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Instagram Error: {e}")
        return False
# ----------------------------------

def process_video(input_path, output_path):
    print("🎬 Editing Video: Speed 1.05x + Big Logo...")
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
        
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", verbose=False, logger=None)
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
    
    r = requests.get(video_url, stream=True)
    with open(raw_video, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): f.write(chunk)

    # 3. Edit Video
    if not process_video(raw_video, processed_video):
        return

    # 4. Upload to YouTube
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

    # 5. Upload to Instagram (Ye naya step hai)
    insta_caption = f"{caption_text}\n.\n.\n{HASHTAGS}"
    post_to_instagram(processed_video, insta_caption)

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
    print("🎉 All Platforms Updated!")

if __name__ == "__main__":
    main()
