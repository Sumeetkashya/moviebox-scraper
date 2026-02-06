import os, requests, json, time, base64, pickle
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- CONFIG ---
PENDING_FOLDER_ID = "1q0fYCs6yAZG6dmlUH6ql4M5eLLbUPa2V"
MOVIEBOX_URL = "https://moviebox.ph/share/post?id=6469190882641300568&package_name=com.community.oneroom"

def get_services():
    # 1. Drive Service (Service Account)
    drive_info = json.loads(os.environ["GDRIVE_API_KEY"])
    drive_creds = service_account.Credentials.from_service_account_info(drive_info)
    
    # 2. YouTube Service (OAuth Token)
    token_data = base64.b64decode(os.environ["YT_TOKEN_BASE64"])
    yt_creds = pickle.loads(token_data)
    if yt_creds.expired and yt_creds.refresh_token:
        yt_creds.refresh(Request())
        
    return build('drive', 'v3', credentials=drive_creds), build('youtube', 'v3', credentials=yt_creds)

def scrape_moviebox():
    headers = {'User-Agent': 'Mozilla/5.0'}
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

def main():
    drive, yt = get_services()
    print("Checking MovieBox...")
    video_url = scrape_moviebox()
    if not video_url:
        print("No new video."); return

    print("Downloading...")
    video_file = "temp_video.mp4"
    r = requests.get(video_url, stream=True)
    with open(video_file, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): f.write(chunk)

    print("Uploading to Google Drive...")
    meta = {'name': f'Krold_{int(time.time())}.mp4', 'parents': [PENDING_FOLDER_ID]}
    media = MediaFileUpload(video_file, mimetype='video/mp4')
    drive.files().create(body=meta, media_body=media).execute()

    print("Posting to YouTube...")
    body = {
        'snippet': {'title': 'Epic Movie Clip #Shorts', 'description': 'Automated by Krold IT', 'categoryId': '22'},
        'status': {'privacyStatus': 'public'}
    }
    yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(video_file)).execute()

    with open("history.txt", "a") as f: f.write(video_url + "\n")
    os.remove(video_file)
    print("Success!")

if __name__ == "__main__": main()
