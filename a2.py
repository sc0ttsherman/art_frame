import os
import time
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk, ImageDraw, ImageFont
import requests

SONGS_FILE = "songs.txt"
ART_FOLDER = "album_art"

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in " .-_").rstrip()

def get_album_name_from_song(song_line):
    # Try to split as "Artist - Song"
    if " - " in song_line:
        artist, title = song_line.split(" - ", 1)
    else:
        artist, title = "", song_line
    # Query Apple API for album info
    params = {
        "term": f"{artist} {title}",
        "media": "music",
        "entity": "song",
        "limit": 1
    }
    resp = requests.get("https://itunes.apple.com/search", params=params)
    if resp.status_code == 200 and resp.json()["resultCount"]:
        result = resp.json()["results"][0]
        album = result.get("collectionName", "")
        artist = result.get("artistName", artist)
        return artist, title, album
    return artist, title, ""

def download_album_art(artist, album, folder):
    if not album:
        return None
    filename = sanitize_filename(f"{artist} - {album}") + ".jpg"
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath):
        return filepath
    params = {
        "term": f"{artist} {album}",
        "media": "music",
        "entity": "album",
        "limit": 1
    }
    resp = requests.get("https://itunes.apple.com/search", params=params)
    if resp.status_code == 200 and resp.json()["resultCount"]:
        result = resp.json()["results"][0]
        art_url = result.get("artworkUrl100", "").replace("100x100bb", "600x600bb")
        if art_url:
            img_data = requests.get(art_url).content
            os.makedirs(folder, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(img_data)
            return filepath
    return None

def create_not_found_image(width, height, message="Album Art Not Found"):
    img = Image.new("RGB", (width, height), color="black")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except Exception:
        font = ImageFont.load_default()
    text_width, text_height = draw.textsize(message, font=font)
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

def monitor_and_display():
    last_song = None
    last_filepath = None

    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.configure(background='black')

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    tk_img = ImageTk.PhotoImage(create_not_found_image(screen_width, screen_height))
    label = Label(root, image=tk_img, bg='black')
    label.pack(expand=True)
    label.image = tk_img

    def poll():
        nonlocal last_song, last_filepath, tk_img
        try:
            if os.path.exists(SONGS_FILE):
                with open(SONGS_FILE, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                song = lines[-1] if lines else ""
            else:
                song = ""
            if song != last_song:
                artist, title, album = get_album_name_from_song(song)
                filepath = download_album_art(artist, album, ART_FOLDER)
                new_img = load_and_resize_image(filepath, root)
                label.configure(image=new_img)
                label.image = new_img
                last_song = song
                last_filepath = filepath
        except Exception:
            # On any error, show not found image but keep running
            nf_img = load_and_resize_image("", root)
            label.configure(image=nf_img)
            label.image = nf_img
        root.after(2000, poll)

    root.bind("<Escape>", lambda e: root.destroy())
    root.bind("<Double-Button-1>", lambda e: root.destroy())
    poll()
    root.mainloop()

if __name__ == "__main__":
    monitor_and_display()