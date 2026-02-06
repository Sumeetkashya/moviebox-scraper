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
INSTA_USER = "uselesss.guys"
INSTA_PASS = "Maav5nik@me"

CAPTIONS = ["Wait for the twist! 😱", "Ekdum kadak scene! 🔥", "Best scene ever? 🍿", "Unexpected ending! 🤯"]
HASHTAGS = "#shorts #reels #trending #viral #movies #cinema #uselessguys #kroldit"

def get_services():
    token_data = base64.b64decode(os.environ["YT_TOKEN_BASE64"])
    creds = pickle.loads(token_data)
    if creds.expired and creds.refresh_token: creds.refresh(Request())
    return build('drive', 'v3', credentials=creds), build('youtube', 'v3', credentials=creds)

def post_to_instagram(video_path, caption):
    print("📸 Instagram Posting: Direct Mode (No Thumbnail)...")
    cl = Client()
    cl.request_timeout = 300 # 5 Minute Timeout
    
    try:
        if "INSTA_SESSION" in os.environ:
            session_json = base64.b64decode(os.environ["INSTA_SESSION"]).decode()
            cl.set_settings(json.loads(session_json))
        cl.login(INSTA_USER, INSTA_PASS)
        
        # Thoda delay taaki login settle ho jaye
        time.sleep(5)
        
        print("📤 Uploading Reel (Letting Insta pick cover)...")
        # ⚠️ Thumbnail argument hata diya hai error fix karne ke liye
        cl.clip_upload(video_path, caption)
        
        print("✅ Instagram Reel Posted Successfully!")
        return True
    except Exception as e:
        print(f"❌ Instagram Error: {e}")
        return False

def process_video(input_path, output_path):
    print("🎬 Video Processing: 720p Lite...")
    try:
        clip = VideoFileClip(input_path)
        
        # ✂️ 9:16 Crop
        w, h = clip.size
        target_ratio = 9/16
        if (w/h) > target_ratio:
            new_width = int(h * target_ratio)
            if new_width % 2 != 0: new_width -= 1
            clip = clip.crop(x1=w/2 - new_width/2, width=new_width, height=h)
        
        # 📏 720p Resize
        clip = clip.resize(height=1280)
        if clip.w % 2 != 0: clip = clip.resize(width=clip.w-1)
        
        # ✂️ Trim > 59s
        if clip.duration > 59: clip = clip.subclip(0, 59)
        final_clip = clip.fx(vfx.speedx, 1.05)
        
        # 🏷️ Logo
        if os.path.exists("logo.png"):
            logo = (ImageClip("logo.png").set_duration(final_clip.duration).resize(height=100)
                    .set_opacity(0.85).margin(right=30, top=80, opacity=0).set_pos(("right", "top")))
            final_clip = CompositeVideoClip([final_clip, logo])

        # 💾 Save Video (Pixel Format Fixed)
        final_clip.write_videofile(
            output_path, codec="libx264", audio_codec="aac", fps=24, 
            preset="medium", bitrate="2500k",
            ffmpeg_params=['-pix_fmt', 'yuv420p'], verbose=False, logger=None
        )
        
        clip.close()
        return True
    except Exception as e:
        print(f"❌ Editing Error: {e}"); return False

def scrape_moviebox():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(MOVIEBOX_URL, headers=headers)
        data = json.loads(BeautifulSoup(r.text, 'html.parser').find('script', id='__NUXT_DATA__').string)
        links = [item for item in data if isinstance(item, str) and item.endswith('.mp4')]
        
        if not os.path.exists("history.txt"): open("history.txt", "w").close()
        with open("history.txt", "r") as f: seen = f.read().splitlines()
        
        for link in links:
            if link not in seen: return link
        return None
    except: return None

def main():
    print("🚀 Krold Mega Bot Live...")
    video_url = scrape_moviebox()
    if not video_url:
        print("💤 No new content."); return

    raw, final = "raw.mp4", "final.mp4"
    
    r = requests.get(video_url, stream=True)
    with open(raw, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): f.write(chunk)

    if not process_video(raw, final): return

    # YouTube (Skip if Full)
    print("📺 Posting to YouTube Shorts...")
    try:
        drive, yt = get_services()
        cap = f"{random.choice(CAPTIONS)} #Shorts"
        body = {'snippet': {'title': cap, 'description': f"{cap}\n{HASHTAGS}", 'categoryId': '22'}, 'status': {'privacyStatus': 'public'}}
        yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(final)).execute()
        print("✅ YouTube Success!")
        with open("history.txt", "a") as f: f.write(video_url + "\n")
    except HttpError as e:
        if "uploadLimitExceeded" in str(e): print("⚠️ YT Quota Full. Moving to Insta...")
        else: print(f"❌ YT Error: {e}")
    except Exception as e: print(f"❌ YT Generic Error: {e}")

    # Instagram
    post_to_instagram(final, f"{random.choice(CAPTIONS)}\n.\n{HASHTAGS}")

    # Drive
    try:
        meta = {'name': f'Krold_{int(time.time())}.mp4', 'parents': [PENDING_FOLDER_ID]}
        drive.files().create(body=meta, media_body=MediaFileUpload(final)).execute()
        print("✅ Drive Backup Done!")
    except: pass

    # Cleanup
    for f in [raw, final]: 
        if os.path.exists(f): os.remove(f)
    print("🎉 All Done!")

if __name__ == "__main__":
    main()
