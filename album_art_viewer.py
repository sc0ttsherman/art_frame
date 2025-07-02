# album_art_viewer.py
import os
import glob
import requests
from PIL import Image, ImageTk
import tkinter as tk
import time

# Folder containing album art
FOLDER = "album_art/"
os.makedirs(FOLDER, exist_ok=True)

# Text file with song list
ALBUM_LIST_FILE = "songs.txt"

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()

def get_album_name_from_song(song_entry):
    """
    Given a song entry (optionally 'Artist - Song'), return (artist, song, album_name)
    """
    if " - " in song_entry:
        artist, song = song_entry.split(" - ", 1)
        query = f"{artist} {song}"
    else:
        artist = ""
        song = song_entry
        query = song_entry
    params = {
        "term": query,
        "media": "music",
        "entity": "song",
        "limit": 1
    }
    response = requests.get("https://itunes.apple.com/search", params=params)
    if response.status_code == 200:
        results = response.json().get("results")
        if results:
            result = results[0]
            album_name = result.get("collectionName")
            artist_name = result.get("artistName")
            return artist_name, song, album_name
    return None, None, None

def download_album_art(album_list_file, folder):
    with open(album_list_file, "r", encoding="utf-8") as f:
        songs = [line.strip() for line in f if line.strip()]
    for entry in songs:
        artist, song, album_name = get_album_name_from_song(entry)
        if not album_name:
            print(f"Could not find album for: {entry}")
            continue
        filename = sanitize_filename(f"{artist} - {album_name}") + ".jpg"
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            print(f"Already exists: {filename}")
            continue
        # Now search for the album art using album name and artist
        query = f"{artist} {album_name}" if artist else album_name
        params = {
            "term": query,
            "media": "music",
            "entity": "album",
            "limit": 5
        }
        response = requests.get("https://itunes.apple.com/search", params=params)
        if response.status_code == 200:
            results = response.json().get("results")
            match = None
            for result in results:
                if (result.get("collectionName", "").lower() == album_name.lower() and
                    result.get("artistName", "").lower() == artist.lower()):
                    match = result
                    break
            if not match and results:
                match = results[0]
            if match:
                art_url = match.get("artworkUrl100")
                if art_url:
                    art_url = art_url.replace("100x100bb", "600x600bb")
                    img_data = requests.get(art_url).content
                    with open(filepath, "wb") as img_file:
                        img_file.write(img_data)
                    print(f"Downloaded: {artist} - {album_name}")
                else:
                    print(f"No artwork found for: {entry}")
            else:
                print(f"No album match found for: {entry}")
        else:
            print(f"API error for: {entry}")

# Download album art for all songs in songs.txt (iterate through all lines)
download_album_art(ALBUM_LIST_FILE, FOLDER)

def display_latest_album_art():
    with open(ALBUM_LIST_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines:
        print("songs.txt is empty.")
        exit(1)
    last_entry = lines[-1]
    artist, song, album_name = get_album_name_from_song(last_entry)
    if not album_name:
        print(f"Could not determine album for: {last_entry}")
        exit(1)
    last_filename = sanitize_filename(f"{artist} - {album_name}") + ".jpg"
    last_filepath = os.path.join(FOLDER, last_filename)
    if not os.path.exists(last_filepath):
        print(f"Album art not found for last song: {last_entry}")
        exit(1)

    # Supported image extensions
    EXTENSIONS = ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif')
    files = []
    for ext in EXTENSIONS:
        files.extend(glob.glob(os.path.join(FOLDER, ext)))

    # Delete all other files in the album_art folder except the one being displayed
    deleted_any = False
    for f in files:
        if os.path.abspath(f) != os.path.abspath(last_filepath):
            try:
                os.remove(f)
                deleted_any = True
            except Exception as e:
                print(f"Error deleting {f}: {e}")

    # Delete songs.txt if any album art was deleted
    if deleted_any and os.path.exists(ALBUM_LIST_FILE):
        try:
            os.remove(ALBUM_LIST_FILE)
            print("Deleted songs.txt because album art was deleted.")
        except Exception as e:
            print(f"Error deleting songs.txt: {e}")

    # Display the album art for the last song in songs.txt fullscreen
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.configure(background='black')

    img = Image.open(last_filepath)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Resize image so height is full screen, maintaining aspect ratio (no stretching)
    img_ratio = img.width / img.height
    new_height = screen_height
    new_width = int(screen_height * img_ratio)
    img = img.resize((new_width, new_height), Image.LANCZOS)
    tk_img = ImageTk.PhotoImage(img)

    label = tk.Label(root, image=tk_img, bg='black')
    label.pack(expand=True)

    root.bind("<Escape>", lambda e: root.destroy())  # Press Esc to exit
    root.bind("<Double-Button-1>", lambda e: root.destroy())  # Double-click to exit

    # Poll for changes to songs.txt in a background loop
    def poll_for_change():
        try:
            with open(ALBUM_LIST_FILE, "r", encoding="utf-8") as f:
                new_lines = [line.strip() for line in f if line.strip()]
            if not new_lines or new_lines[-1] != last_entry:
                root.destroy()
                return
        except Exception:
            pass
        root.after(2000, poll_for_change)  # Check every 2 seconds

    poll_for_change()
    root.mainloop()

while True:
    download_album_art(ALBUM_LIST_FILE, FOLDER)  # Wait for download to finish before displaying
    display_latest_album_art()
    # Short pause to avoid rapid looping if file is changing quickly
    time.sleep(1)