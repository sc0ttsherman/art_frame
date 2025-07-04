# album_art_viewer.py
import os
import glob
import requests
from PIL import Image, ImageTk, ImageDraw, ImageFont
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
    if not songs:
        return
    entry = songs[-1]  # Only process the last song
    artist, song, album_name = get_album_name_from_song(entry)
    if not album_name:
        print(f"Could not find album for: {entry}")
        return
    filename = sanitize_filename(f"{artist} - {album_name}") + ".jpg"
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath):
        print(f"Already exists: {filename}")
        return
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

def create_not_found_image(width, height, message="The Album Art Could Not Be Fetched"):
    img = Image.new("RGB", (width, height), color="black")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except Exception:
        font = ImageFont.load_default()
    # Use textbbox instead of textsize for newer Pillow versions
    bbox = draw.textbbox((0, 0), message, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    draw.text((x, y), message, fill="white", font=font)
    return img

def load_and_resize_image(filepath, root):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    try:
        if filepath and os.path.exists(filepath):
            img = Image.open(filepath)
            img_ratio = img.width / img.height
            new_height = screen_height
            new_width = int(screen_height * img_ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)
        else:
            img = create_not_found_image(screen_width, screen_height)
    except Exception:
        img = create_not_found_image(screen_width, screen_height)
    return ImageTk.PhotoImage(img)

def display_latest_album_art():
    last_entry = ""
    last_filepath = ""

    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.configure(background='black')

    tk_img = load_and_resize_image("", root)
    label = tk.Label(root, image=tk_img, bg='black')
    label.pack(expand=True)
    label.image = tk_img

    root.bind("<Escape>", lambda e: root.destroy())
    root.bind("<Double-Button-1>", lambda e: root.destroy())

    def poll_for_change():
        nonlocal last_entry, last_filepath
        try:
            with open(ALBUM_LIST_FILE, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            new_last_entry = lines[-1] if lines else ""
            artist, song, album_name = get_album_name_from_song(new_last_entry) if new_last_entry else ("", "", "")
            new_last_filename = sanitize_filename(f"{artist} - {album_name}") + ".jpg" if album_name else ""
            new_last_filepath = os.path.join(FOLDER, new_last_filename) if new_last_filename else ""

            # Download album art for the new last song if needed
            if new_last_entry and (not os.path.exists(new_last_filepath) or new_last_entry != last_entry):
                download_album_art(ALBUM_LIST_FILE, FOLDER)

            if new_last_entry != last_entry or new_last_filepath != last_filepath:
                new_tk_img = load_and_resize_image(new_last_filepath, root)
                label.configure(image=new_tk_img)
                label.image = new_tk_img
                last_entry = new_last_entry
                last_filepath = new_last_filepath
        except Exception:
            # On any error, just show not found image and keep running
            new_tk_img = load_and_resize_image("", root)
            label.configure(image=new_tk_img)
            label.image = new_tk_img
        root.after(2000, poll_for_change)

    poll_for_change()
    root.mainloop()

display_latest_album_art()