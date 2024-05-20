import time
import traceback
import asyncio
import pyautogui
import pydirectinput
import pytesseract
import pygetwindow as gw
from PIL import ImageGrab
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

class NoMediaRunningException(Exception):
    pass

# Spotify credentials
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID', 'your_default_client_id')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET', 'your_default_client_secret')
SPOTIPY_REDIRECT_URI = 'http://localhost:25565'

# Function to retrieve media information
async def get_media_info():
    sessions = await MediaManager.request_async()
    current_session = sessions.get_current_session()
    if current_session:
        info = await current_session.try_get_media_properties_async()
        info_dict = {song_attr: getattr(info, song_attr) for song_attr in dir(info) if song_attr[0] != '_'}
        info_dict['genres'] = list(info_dict['genres'])

        pbinfo = current_session.get_playback_info()
        info_dict['status'] = pbinfo.playback_status

        return info_dict
    else:
        raise NoMediaRunningException("No media source running.")

# Function to perform OCR within the specified box
def perform_ocr(box):
    screenshot = ImageGrab.grab(bbox=box, include_layered_windows=False, all_screens=True)
    text = pytesseract.image_to_string(screenshot)
    return text.strip()

# Search song on Spotify and add to queue
def queue_song(song_name, artist_name=None):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                                   client_secret=SPOTIPY_CLIENT_SECRET,
                                                   redirect_uri=SPOTIPY_REDIRECT_URI,
                                                   scope="user-modify-playback-state"))

    if artist_name:
        results = sp.search(q=f'track:{song_name} artist:{artist_name}', limit=1, type='track')
    else:
        results = sp.search(q=song_name, limit=1, type='track')

    if results['tracks']['items']:
        song_uri = results['tracks']['items'][0]['uri']
        sp.add_to_queue(uri=song_uri)
        print(f"Added '{song_name}' to Spotify queue.")
        return results['tracks']['items'][0]
    else:
        print(f"Song '{song_name}' by '{artist_name}' not found on Spotify.")
        return None

async def process_media_info():
    try:
        current_media_info = await get_media_info()
        return current_media_info
    except NoMediaRunningException:
        await asyncio.sleep(1.5)
    except Exception as e:
        print("!!!", e, traceback.format_exc())
        await asyncio.sleep(1.5)

async def main():
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    last_queued_song = None
    last_song_title = None
    last_song_artist = None
    ambnp_ready = None
    first_run = True
    queued_songs = []
    ocr_box = (2890, 307, 3240, 330)  # Define the OCR box coordinates

    while True:
        current_media_info = await process_media_info()
        if not current_media_info:
            continue

        song_artist, song_title = (current_media_info['artist'], current_media_info['title'])
        text_on_screen = perform_ocr(ocr_box)
        print(f"Text within the box: {text_on_screen}")

        if song_title != last_song_title or song_artist != last_song_artist:
            last_song_title = song_title
            last_song_artist = song_artist
            ambnp_ready = True

            roblox_windows = gw.getWindowsWithTitle("Roblox")
            second_monitor_roblox_window = next((window for window in roblox_windows if window.topleft[0] >= 1920), None)

            try:
                if second_monitor_roblox_window and (first_run or ambnp_ready):
                    pyautogui.press('altleft')
                    second_monitor_roblox_window.activate()
                    print("Brought Roblox forward")
                    await asyncio.sleep(1)

                message = f"Now playing {song_title} by {song_artist}\n"
                pydirectinput.press('/')
                pyautogui.typewrite(message)
                pydirectinput.press('enter')
                pydirectinput.press("space")
                first_run = False

            except gw.PyGetWindowException as e:
                print(f"Error occurred while activating Roblox window: {e}")

        if "AMBp" in text_on_screen:
            print("Found 'AMBp' to split and extract")
            parts = text_on_screen.split("AMBp", 1)
            print("Parts after split: ", parts)
            
            if len(parts) == 2:
                song_info = parts[1].strip().split(" by ")
                print(song_info)
                
                if len(song_info) == 2:
                    song_name, artist_name = song_info
                    print("Song name:", song_name)
                    print("Artist:", artist_name)
                    if song_name != last_queued_song:
                        song = queue_song(song_name, artist_name)
                        if song:
                            queued_songs.append(song)
                            last_queued_song = song_name
                            print("Queued Request Seen")
                    else:
                        print("Same song already queued, skipping...")

        if "AMBnp" in text_on_screen and ambnp_ready:
            current_media_info = await get_media_info()
            if current_media_info:
                pyautogui.press('altleft')
                second_monitor_roblox_window.activate()
                print("Brought Roblox forward")
                await asyncio.sleep(1)
                pydirectinput.press('/')
                pyautogui.typewrite(message)
                pydirectinput.press('enter')
                pydirectinput.press("space")
                ambnp_ready = False

        if "AMBn" in text_on_screen:
            print("Found 'AMBn' to announce next song")
            if queued_songs:
                next_song = queued_songs[0]
                next_song_title = next_song['name']
                next_song_artist = ", ".join(artist['name'] for artist in next_song['artists'])
                next_song_message = f"Next song in queue: {next_song_title} by {next_song_artist}"
                print(next_song_message)

                try:
                    if second_monitor_roblox_window:
                        pyautogui.press('altleft')
                        second_monitor_roblox_window.activate()
                        print("Brought Roblox forward")
                        await asyncio.sleep(1)
                        
                        pydirectinput.press('/')
                        pyautogui.typewrite(next_song_message)
                        pydirectinput.press('enter')
                        pydirectinput.press("space")
                except gw.PyGetWindowException as e:
                    print(f"Error occurred while activating Roblox window: {e}")
            else:
                print("Queue is empty. No next song to announce.")

        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
