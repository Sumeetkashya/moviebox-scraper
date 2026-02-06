import os, requests, json, time, base64, pickle, random
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from instagrapi import Client
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, vfx

# --- PIL FIX ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIG ---
INSTA_USER = "uselesss.guys"
INSTA_PASS = "Maav5nik@me"
SESSION_FILE = "insta_session.json"
CAPTIONS = ["Wait for the twist! 😱", "Ekdum kadak scene! 🔥", "Best scene ever? 🍿"]
HASHTAGS = "#shorts #reels #trending #viral #movies #cinema #uselessguys #kroldit"

def get_services():
    token_data = base64.b64decode(os.environ["YT_TOKEN_BASE64"])
    creds = pickle.loads(token_data)
    if creds.expired and creds.refresh_token: creds.refresh(Request())
    return build('drive', 'v3', credentials=creds), build('youtube', 'v3', credentials=creds)

def post_to_instagram(video_path, thumbnail_path, caption):
    print("📸 Instagram: Attempting Session-based Login...")
    cl = Client()
    
    try:
        # 1. Check if session exists in Secrets
        if "INSTA_SESSION" in os.environ:
            session_data = base64.b64decode(os.environ["INSTA_SESSION"]).decode()
            cl.set_settings(json.loads(session_data))
            print("🔑 Session loaded from Secrets.")

        # 2. Try to Login/Verify
        cl.login(INSTA_USER, INSTA_PASS)
        
        # 3. Upload
        print("📤 Uploading Reel...")
        time.sleep(random.randint(10, 20))
        cl.video_upload(video_path, caption, thumbnail=thumbnail_path)
        print("✅ Instagram Reel Posted Successfully!")
        return True
    except Exception as e:
        print(f"❌ Instagram Error: {e}")
        return False

def process_video(input_path, output_path, thumb_path):
    print("🎬 Processing Video (Standard 720p)...")
    try:
        clip = VideoFileClip(input_path)
        w, h = clip.size
        if (w/h) > (9/16):
            new_w = int(h * (9/16))
            if new_w % 2 != 0: new_w -= 1
            clip = clip.crop(x1=w/2 - new_w/2, width=new_w, height=h)
        
        clip = clip.resize(height=1280)
        if clip.w % 2 != 0: clip = clip.resize(width=clip.w-1)
        if clip.duration > 59: clip = clip.subclip(0, 59)
        final = clip.fx(vfx.speedx, 1.05)
        
        if os.path.exists("logo.png"):
            logo = (ImageClip("logo.png").set_duration(final.duration).resize(height=100)
                    .set_opacity(0.85).margin(right=30, top=80, opacity=0).set_pos(("right", "top")))
            final = CompositeVideoClip([final, logo])

        final.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, preset="medium", 
                             bitrate="2500k", ffmpeg_params=['-movflags', '+faststart', '-pix_fmt', 'yuv420p'], 
                             verbose=False, logger=None)
        
        PIL.Image.fromarray(final.get_frame(1.0)).convert("RGB").save(thumb_path, quality=95)
        clip.close()
        return True
    except Exception as e:
        print(f"❌ Editing Error: {e}"); return False

def main():
    print("🚀 Krold Bot Restarted...")
    video_url = "https://macdn.aoneroom.com/media/vone/2023/02/15/c89b42c62f44c1bc48231f551984e901-sd.mp4"
    raw, final, thumb = "raw.mp4", "final.mp4", "thumb.jpg"
    
    # Download & Edit
    r = requests.get(video_url, stream=True)
    with open(raw, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): f.write(chunk)
    if not process_video(raw, final, thumb): return

    # YouTube (With Quota Handling)
    try:
        _, yt = get_services()
        cap = f"{random.choice(CAPTIONS)} #Shorts"
        yt.videos().insert(part="snippet,status", body={'snippet': {'title': cap, 'categoryId': '22'}, 'status': {'privacyStatus': 'public'}}, 
                          media_body=MediaFileUpload(final)).execute()
        print("✅ YouTube Done!")
    except Exception as e:
        print(f"⚠️ YouTube skipped (Limit/Error): {e}")

    # Instagram
    post_to_instagram(final, thumb, f"{random.choice(CAPTIONS)}\n.\n{HASHTAGS}")

    # Cleanup
    for f in [raw, final, thumb]: 
        if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    main()
