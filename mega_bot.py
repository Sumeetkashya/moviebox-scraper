import os, requests, json, time, base64, pickle, random
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from instagrapi import Client
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, vfx

# --- 🛠️ PIL FIX ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ------------------

# --- CONFIG ---
PENDING_FOLDER_ID = "1q0fYCs6yAZG6dmlUH6ql4M5eLLbUPa2V"
MOVIEBOX_URL = "https://moviebox.ph/share/post?id=6469190882641300568&package_name=com.community.oneroom"
INSTA_USER = "uselesss.guys"
INSTA_PASS = "Maav5nik@me"

CAPTIONS = [
    "Wait for the twist! 😱", "Ekdum kadak scene! 🔥", 
    "Ye ending miss mat karna! ✨", "Legendary movie moment 🎬", 
    "Best scene ever? 🍿"
]
HASHTAGS = "#shorts #reels #trending #viral #movies #cinema #uselessguys #kroldit"

def get_services():
    token_data = base64.b64decode(os.environ["YT_TOKEN_BASE64"])
    creds = pickle.loads(token_data)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds), build('youtube', 'v3', credentials=creds)

def post_to_instagram(video_path, thumbnail_path, caption):
    print("📸 Posting to Instagram (Compressed Mode)...")
    cl = Client()
    # Timeout badhakar 5 minute kar diya
    cl.request_timeout = 300 
    
    try:
        # Session Load
        if "INSTA_SESSION" in os.environ:
            print("🔑 Loading Session...")
            session_b64 = os.environ["INSTA_SESSION"]
            session_json = base64.b64decode(session_b64).decode()
            cl.set_settings(json.loads(session_json))
        
        cl.login(INSTA_USER, INSTA_PASS)
        
        # Upload
        print("📤 Uploading Reel (Please wait, might take time)...")
        # Delay taaki connection stabilize ho
        time.sleep(10) 
        cl.clip_upload(video_path, caption, thumbnail=thumbnail_path)
        print("✅ Instagram Reel Posted Successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Instagram Error: {e}")
        return False

def process_video(input_path, output_path, thumb_path):
    print("🎬 Editing Video (Compressing for Insta)...")
    try:
        clip = VideoFileClip(input_path)
        # Duration check: Agar video 60s se bada hai, toh trim karo (Reels limit)
        if clip.duration > 59:
            print("✂️ Trimming video to 59s...")
            clip = clip.subclip(0, 59)
            
        final_clip = clip.fx(vfx.speedx, 1.05)
        
        if os.path.exists("logo.png"):
            logo = (ImageClip("logo.png")
                    .set_duration(final_clip.duration)
                    .resize(height=120)
                    .set_opacity(0.85)
                    .margin(right=25, top=25, opacity=0)
                    .set_pos(("right", "top")))
            final_clip = CompositeVideoClip([final_clip, logo])
        
        # --- 🛠️ COMPRESSION FIX ---
        # preset='medium' se file size chhota hoga, upload fast hoga
        # bitrate='3000k' quality maintain karega par size control mein rakhega
        final_clip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24, 
            preset="medium",   # <--- Changed from 'ultrafast' to 'medium'
            bitrate="3000k",   # <--- Limit bitrate
            ffmpeg_params=['-pix_fmt', 'yuv420p'], 
            verbose=False, 
            logger=None
        )
        
        # Thumbnail
        print("🖼️ Generating Thumbnail...")
        frame = final_clip.get_frame(1.0)
        img = PIL.Image.fromarray(frame).convert("RGB")
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
        data = json.loads(BeautifulSoup(r.text, 'html.parser').find('script', id='__NUXT_DATA__').string)
        links = [item for item in data if isinstance(item, str) and item.endswith('.mp4')]
        
        if not os.path.exists("history.txt"): open("history.txt", "w").close()
        with open("history.txt", "r") as f: seen = f.read().splitlines()
        
        for link in links:
            if link not in seen: return link
        return None
    except: return None

def main():
    print("🚀 Krold Bot Started...")
    video_url = scrape_moviebox()
    if not video_url:
        print("💤 No new video found."); return

    raw, final, thumb = "raw.mp4", "final.mp4", "thumb.jpg"
    
    # Download
    print("📥 Downloading Video...")
    r = requests.get(video_url, stream=True)
    with open(raw, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): f.write(chunk)

    # Edit
    if not process_video(raw, final, thumb): return

    # YouTube Upload
    print("📺 Posting to YouTube Shorts...")
    try:
        drive, yt = get_services()
        cap = f"{random.choice(CAPTIONS)} #Shorts"
        body = {'snippet': {'title': cap, 'description': f"{cap}\n{HASHTAGS}", 'categoryId': '22'}, 'status': {'privacyStatus': 'public'}}
        yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(final)).execute()
        print("✅ YouTube Done!")
        with open("history.txt", "a") as f: f.write(video_url + "\n")
    except Exception as e: print(f"❌ YouTube Error: {e}")

    # Instagram Upload
    post_to_instagram(final, thumb, f"{random.choice(CAPTIONS)}\n.\n{HASHTAGS}")

    # Drive Backup
    try:
        print("☁️ Backing up to Drive...")
        meta = {'name': f'Krold_{int(time.time())}.mp4', 'parents': [PENDING_FOLDER_ID]}
        drive.files().create(body=meta, media_body=MediaFileUpload(final)).execute()
        print("✅ Drive Backup Done!")
    except: pass

    # Cleanup
    for f in [raw, final, thumb]: 
        if os.path.exists(f): os.remove(f)
    print("🎉 All Tasks Completed!")

if __name__ == "__main__":
    main()
