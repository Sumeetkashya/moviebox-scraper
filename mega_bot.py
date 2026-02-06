import os, requests, json, time, base64, pickle, random
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from instagrapi import Client
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, vfx

# --- 🛠️ PIL FIX ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIG ---
PENDING_FOLDER_ID = "1q0fYCs6yAZG6dmlUH6ql4M5eLLbUPa2V"
MOVIEBOX_URL = "https://moviebox.ph/share/post?id=6469190882641300568&package_name=com.community.oneroom"
# Note: Password ki zaroorat nahi hai ab, sirf session chalega
INSTA_USER = "uselesss.guys"

CAPTIONS = ["Wait for the twist! 😱", "Ekdum kadak scene! 🔥", "Best scene ever? 🍿", "Unexpected ending! 🤯"]
HASHTAGS = "#shorts #reels #trending #viral #movies #cinema #uselessguys #kroldit"

def get_services():
    try:
        token_data = base64.b64decode(os.environ["YT_TOKEN_BASE64"])
        creds = pickle.loads(token_data)
        if creds.expired and creds.refresh_token: creds.refresh(Request())
        return build('drive', 'v3', credentials=creds), build('youtube', 'v3', credentials=creds)
    except Exception as e:
        print(f"⚠️ Google Auth Error: {e}")
        return None, None

def post_to_instagram(video_path, thumbnail_path, caption):
    print("📸 Instagram: Loading Saved Session (No Login)...")
    cl = Client()
    cl.request_timeout = 300 
    
    try:
        # --- 🔑 ONLY SESSION LOAD (No Password Login) ---
        if "INSTA_SESSION" in os.environ:
            print("🔓 Decoding Session String...")
            session_data = base64.b64decode(os.environ["INSTA_SESSION"]).decode()
            cl.set_settings(json.loads(session_data))
            print("✅ Session Loaded Successfully!")
        else:
            print("❌ Error: INSTA_SESSION secret not found!")
            return False

        # Thoda delay taaki connection ban jaye
        time.sleep(5)
        
        print("📤 Uploading Video...")
        # Thumbnail file use kar rahe hain taaki cover photo sahi aaye
        cl.video_upload(video_path, caption, thumbnail=thumbnail_path)
        
        print("✅ Instagram Reel Posted Successfully!")
        return True

    except Exception as e:
        print(f"❌ Instagram Error: {e}")
        # Agar session expire ho gaya ho toh batayega
        if "login_required" in str(e):
            print("⚠️ Session Expired: Naya session generate karna padega.")
        return False

def process_video(input_path, output_path, thumb_path):
    print("🎬 Processing Video (720p Lite)...")
    try:
        clip = VideoFileClip(input_path)
        
        # ✂️ 9:16 Crop
        w, h = clip.size
        if (w/h) > (9/16):
            new_w = int(h * (9/16))
            if new_w % 2 != 0: new_w -= 1
            clip = clip.crop(x1=w/2 - new_w/2, width=new_w, height=h)
        
        # 📏 Resize & Trim
        clip = clip.resize(height=1280)
        if clip.w % 2 != 0: clip = clip.resize(width=clip.w-1)
        if clip.duration > 59: clip = clip.subclip(0, 59)
        final = clip.fx(vfx.speedx, 1.05)
        
        # 🏷️ Logo
        if os.path.exists("logo.png"):
            logo = (ImageClip("logo.png").set_duration(final.duration).resize(height=100)
                    .set_opacity(0.85).margin(right=30, top=80, opacity=0).set_pos(("right", "top")))
            final = CompositeVideoClip([final, logo])

        # 💾 Save (FastStart + yuv420p)
        final.write_videofile(
            output_path, codec="libx264", audio_codec="aac", fps=24, 
            preset="medium", bitrate="2500k",
            ffmpeg_params=['-movflags', '+faststart', '-pix_fmt', 'yuv420p'], 
            verbose=False, logger=None
        )
        
        # 🖼️ Thumbnail
        frame = final.get_frame(1.0)
        PIL.Image.fromarray(frame).convert("RGB").save(thumb_path, quality=95)
        
        clip.close()
        return True
    except Exception as e:
        print(f"❌ Editing Error: {e}"); return False

def scrape_moviebox():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(MOVIEBOX_URL, headers=headers)
        # Yahan script tag dhoondh kar JSON parse kar rahe hain
        soup = BeautifulSoup(r.text, 'html.parser')
        script = soup.find('script', id='__NUXT_DATA__')
        if not script: return None
        
        data = json.loads(script.string)
        # List mein se .mp4 link nikalna
        links = [item for item in data if isinstance(item, str) and item.endswith('.mp4')]
        
        if not os.path.exists("history.txt"): open("history.txt", "w").close()
        with open("history.txt", "r") as f: seen = f.read().splitlines()
        
        for link in links:
            if link not in seen: return link
        return None
    except: return None

def main():
    print("🚀 Krold Bot Live...")
    
    # 1. Scraping
    video_url = scrape_moviebox()
    if not video_url:
        print("💤 No new content."); return

    raw, final, thumb = "raw.mp4", "final.mp4", "thumb.jpg"
    
    # 2. Downloading
    print(f"📥 Downloading: {video_url}")
    try:
        r = requests.get(video_url, stream=True)
        with open(raw, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024): f.write(chunk)
    except Exception as e:
        print(f"❌ Download Error: {e}"); return

    # 3. Processing
    if not process_video(raw, final, thumb): return

    # 4. YouTube (Skip if Quota Full)
    print("📺 Posting to YouTube Shorts...")
    try:
        drive, yt = get_services()
        if yt:
            cap = f"{random.choice(CAPTIONS)} #Shorts"
            yt.videos().insert(part="snippet,status", 
                body={'snippet': {'title': cap, 'categoryId': '22'}, 'status': {'privacyStatus': 'public'}}, 
                media_body=MediaFileUpload(final)).execute()
            print("✅ YouTube Done!")
            with open("history.txt", "a") as f: f.write(video_url + "\n")
    except HttpError as e:
        if "uploadLimitExceeded" in str(e): print("⚠️ YT Quota Full. Skipping...")
        else: print(f"❌ YT Error: {e}")
    except Exception as e:
        print(f"❌ YT Generic Error: {e}")

    # 5. Instagram (Session Mode)
    post_to_instagram(final, thumb, f"{random.choice(CAPTIONS)}\n.\n{HASHTAGS}")

    # 6. Drive Backup
    try:
        print("☁️ Backing up to Drive...")
        meta = {'name': f'Krold_{int(time.time())}.mp4', 'parents': [PENDING_FOLDER_ID]}
        drive.files().create(body=meta, media_body=MediaFileUpload(final)).execute()
        print("✅ Drive Backup Done!")
    except: pass

    # Cleanup
    for f in [raw, final, thumb]: 
        if os.path.exists(f): os.remove(f)
    print("🎉 Workflow Complete!")

if __name__ == "__main__":
    main()
