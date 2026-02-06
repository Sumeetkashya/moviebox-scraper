import os
import requests
import json
import time
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION ---
PENDING_FOLDER_ID = "1q0fYCs6yAZG6dmlUH6ql4M5eLLbUPa2V"
# MovieBox URL (Is URL ko kabhi kabhi check karte rehna agar link change ho)
MOVIEBOX_URL = "https://moviebox.ph/share/post?id=6469190882641300568&package_name=com.community.oneroom"
HISTORY_FILE = "history.txt"

def get_drive_service():
    # GitHub Secrets se Key uthana
    info = json.loads(os.environ["GDRIVE_API_KEY"])
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def scrape_video_link():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(MOVIEBOX_URL, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    data_script = soup.find('script', id='__NUXT_DATA__')
    if not data_script:
        print("Data script nahi mila.")
        return None
    
    try:
        data = json.loads(data_script.string)
    except json.JSONDecodeError:
        print("JSON parse nahi hua.")
        return None

    # Link dhoondhna (.mp4)
    links = [item for item in data if isinstance(item, str) and item.endswith('.mp4')]
    
    # History check
    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, "w").close()
    
    with open(HISTORY_FILE, "r") as f:
        seen = f.read().splitlines()
    
    for link in links:
        if link not in seen:
            return link
    return None

def main():
    print("Scraping shuru...")
    video_url = scrape_video_link()
    
    if not video_url:
        print("Koi naya video nahi mila (Sab purane hain).")
        # Ensure history file exists even if no new video, to avoid git error
        if not os.path.exists(HISTORY_FILE):
            open(HISTORY_FILE, "w").close()
        return

    print(f"Naya video mila: {video_url}")
    
    # Download
    try:
        video_data = requests.get(video_url).content
        filename = f"mb_video_{int(time.time())}.mp4"
        with open(filename, "wb") as f:
            f.write(video_data)
        
        # Upload to Drive
        print("Drive par upload ho raha hai...")
        service = get_drive_service()
        meta = {'name': filename, 'parents': [PENDING_FOLDER_ID]}
        media = MediaFileUpload(filename, mimetype='video/mp4')
        service.files().create(body=meta, media_body=media).execute()
        print("Upload Successful!")

        # Update History
        with open(HISTORY_FILE, "a") as f:
            f.write(video_url + "\n")
        
        # Cleanup
        if os.path.exists(filename):
            os.remove(filename)

    except Exception as e:
        print(f"Process mein galti hui: {e}")

if __name__ == "__main__":
    main()
