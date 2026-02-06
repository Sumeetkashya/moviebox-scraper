import os, requests, json, time, base64, pickle, random
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, vfx

# --- CONFIGURATION ---
PENDING_FOLDER_ID = "1q0fYCs6yAZG6dmlUH6ql4M5eLLbUPa2V"
MOVIEBOX_URL = "https://moviebox.ph/share/post?id=6469190882641300568&package_name=com.community.oneroom"

# --- HASHTAGS & CAPTIONS ---
HASHTAGS = """
#shorts #trending #viral #movies #cinema #bollywood #hollywood #action 
#bestscenes #uselessguys #kroldit #foryou #fyp #movieclips #mustwatch 
#entertainment #film #drama #suspense #shortsvideo
"""

CAPTIONS = [
    "Wait for the twist! 😱",
    "Ekdum kadak scene! 🔥",
    "Ye ending miss mat karna! ✨",
    "Legendary movie moment 🎬",
    "Best scene ever? 🍿",
    "You won't believe this! 🤯",
    "Pure goosebumps moment 🥶"
]

def get_services():
    token_data = base64.b64decode(os.environ["YT_TOKEN_BASE64"])
    creds = pickle.loads(token_data)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds), build('youtube', 'v3', credentials=creds)

def process_video(input_path, output_path):
    print("🎬 Editing Video: Speed 1.05x + Big Logo...")
    try:
        clip = VideoFileClip(input_path)
        
        # 1. Speed badhao (1.05x)
        final_clip = clip.fx(vfx.speedx, 1.05)
        
        # 2. Logo Setup (Bada size: 120px)
        if os.path.exists("logo.png"):
            print("✅ Logo mil gaya, laga raha hoon...")
            logo = (ImageClip("logo.png")
                    .set_duration(final_clip.duration)
                    .resize(height=120)   
                    .set_opacity(0.85)    
                    .margin(right=25, top=25, opacity=0) 
                    .set_pos(("right", "top")))
            
            final_clip = CompositeVideoClip([final_clip, logo])
        else:
            print("⚠️ Warning: 'logo.png' nahi mila! Bina logo ke proceed kar raha hoon.")
        
        # Rendering
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
    print("🚀 Bot Started...")
    try:
        drive, yt = get_services()
    except Exception as e:
        print(f"❌ Login Error: {e}"); return

    # Step 1: Scrape
    print("🔍 Searching MovieBox...")
    video_url = scrape_moviebox()
    if not video_url:
        print("💤 Koi naya video nahi mila."); return

    # Step 2: Download
    print(f"📥 Downloading: {video_url}")
    raw_video = "raw_video.mp4"
    processed_video = "final_video.mp4"
    r = requests.get(video_url, stream=True)
    with open(raw_video, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): f.write(chunk)

    # Step 3: Edit
    if not process_video(raw_video, processed_video):
        print("❌ Video Process Failed!"); return

    # Step 4: Drive Upload
    print("☁️ Uploading to Google Drive...")
    try:
        meta = {'name': f'Krold_Auto_{int(time.time())}.mp4', 'parents': [PENDING_FOLDER_ID]}
        media = MediaFileUpload(processed_video, mimetype='video/mp4')
        drive.files().create(body=meta, media_body=media).execute()
        print("✅ Drive Upload Done!")
    except Exception as e:
        print(f"⚠️ Drive Error: {e}")

    # Step 5: YouTube Upload
    print("📺 Posting to YouTube...")
    try:
        selected_caption = random.choice(CAPTIONS)
        full_description = f"{selected_caption}\n\nAutomated by Krold IT.\n{HASHTAGS}"
        
        body = {
            'snippet': {
                'title': f"{selected_caption} #Shorts",
                'description': full_description,
                'categoryId': '22'
            },
            'status': {'privacyStatus': 'public'}
        }
        
        media_yt = MediaFileUpload(processed_video, chunksize=-1, resumable=True)
        yt.videos().insert(part="snippet,status", body=body, media_body=media_yt).execute()
        print("✅ YouTube Upload Successful!")
        with open("history.txt", "a") as f: f.write(video_url + "\n")
        
    except Exception as e:
        print(f"❌ YouTube Error: {e}")

    # Cleanup
    if os.path.exists(raw_video): os.remove(raw_video)
    if os.path.exists(processed_video): os.remove(processed_video)
    print("🎉 All Tasks Completed!")

if __name__ == "__main__":
    main()
