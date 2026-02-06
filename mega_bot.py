import os, requests, json, time, base64, pickle
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- CONFIGURATION ---
PENDING_FOLDER_ID = "1q0fYCs6yAZG6dmlUH6ql4M5eLLbUPa2V"
MOVIEBOX_URL = "https://moviebox.ph/share/post?id=6469190882641300568&package_name=com.community.oneroom"

def get_services():
    # Hum sirf tumhare Personal Token (YT_TOKEN_BASE64) ka use karenge
    # Isme Drive aur YouTube dono ki permission hai
    token_data = base64.b64decode(os.environ["YT_TOKEN_BASE64"])
    creds = pickle.loads(token_data)
    
    # Token expire ho toh refresh karo
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        
    # Ek hi 'creds' se dono services banengi
    drive_service = build('drive', 'v3', credentials=creds)
    youtube_service = build('youtube', 'v3', credentials=creds)
    
    return drive_service, youtube_service

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
        print(f"Scraping Error: {e}")
        return None

def main():
    print("🚀 Bot Started...")
    try:
        drive, yt = get_services()
    except Exception as e:
        print(f"Login Error: {e}")
        return

    # STEP 1: Video Dhoondho
    print("Searching MovieBox...")
    video_url = scrape_moviebox()
    if not video_url:
        print("❌ Koi naya video nahi mila."); return

    # STEP 2: Download karo
    print(f"📥 Downloading: {video_url}")
    video_file = "temp_video.mp4"
    r = requests.get(video_url, stream=True)
    with open(video_file, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): f.write(chunk)

    # STEP 3: Google Drive pe Upload karo (Personal Account se)
    print("☁️ Uploading to Google Drive...")
    meta = {'name': f'Krold_Auto_{int(time.time())}.mp4', 'parents': [PENDING_FOLDER_ID]}
    media = MediaFileUpload(video_file, mimetype='video/mp4')
    # Ab ye fail nahi hoga kyunki ye tumhari storage use karega
    drive_file = drive.files().create(body=meta, media_body=media).execute()
    print(f"✅ Drive Upload Done! ID: {drive_file.get('id')}")

    # STEP 4: YouTube pe Post karo
    print("📺 Posting to YouTube Shorts...")
    body = {
        'snippet': {
            'title': 'Viral Movie Scene 🎬 #Shorts #Movies',
            'description': 'Automated by Krold IT Solutions Bot 🤖',
            'categoryId': '22'
        },
        'status': {'privacyStatus': 'public'}
    }
    
    media_yt = MediaFileUpload(video_file, chunksize=-1, resumable=True)
    yt.videos().insert(part="snippet,status", body=body, media_body=media_yt).execute()
    print("✅ YouTube Upload Successful!")

    # Cleanup & History
    with open("history.txt", "a") as f: f.write(video_url + "\n")
    os.remove(video_file)
    print("🎉 All Tasks Completed!")

if __name__ == "__main__":
    main()
