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

class NoMediaRunningException(Exception):
    pass

# Spotify credentials
SPOTIPY_CLIENT_ID = ''
SPOTIPY_CLIENT_SECRET = ''
SPOTIPY_REDIRECT_URI = 'http://localhost:25565'

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope="user-read-playback-state user-modify-playback-state"))

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
def perform_ocr():
    box = (2890, 307, 3240, 330)
    screenshot = ImageGrab.grab(bbox=box, include_layered_windows=False, all_screens=True)
    text = pytesseract.image_to_string(screenshot)
    return text.strip()

# Function to get the next song in the Spotify queue
def get_next_song_in_queue():
    try:
        queue = sp.queue()
        if queue['queue']:
            next_song = queue['queue'][0]
            return next_song['name'], next_song['artists'][0]['name']
        else:
            return None, None
    except Exception as e:
        print("Error retrieving Spotify queue:", e)
        return None, None

# Function to queue a song on Spotify
def queue_song(song_name, artist_name=None):
    if artist_name:
        results = sp.search(q=f'track:{song_name} artist:{artist_name}', limit=1, type='track')
    else:
        results = sp.search(q=song_name, limit=1, type='track')
    if results['tracks']['items']:
        song_uri = results['tracks']['items'][0]['uri']
        sp.add_to_queue(uri=song_uri)
        print(f"Added '{song_name}' to Spotify queue.")
        return True
    else:
        print(f"Song '{song_name}' by '{artist_name}' not found on Spotify.")
        return False

async def main():
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    last_queued_song = None
    last_song_title = None
    last_song_artist = None
    ambnp_ready = None
    first_run = True

    while True:
        try:
            current_media_info = await get_media_info()
        except NoMediaRunningException:
            time.sleep(1.5)
            continue
        except Exception as e:
            print("!!!", e, traceback.format_exc())
            time.sleep(1.5)
            continue

        song_artist, song_title = (current_media_info['artist'], current_media_info['title'])
        text_on_screen = perform_ocr()
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
                    time.sleep(1)
                pydirectinput.press('/')
                message = f"Now playing {song_title} by {song_artist}\n"
                pyautogui.typewrite(message)
                pydirectinput.press('enter')
                pydirectinput.press("space")
                first_run = False
            except gw.PyGetWindowException as e:
                print(f"Error occurred while activating Roblox window: {e}")

        if "AMBp" in text_on_screen:
            print("Found 'AMBp' to split and extract")
            parts = text_on_screen.split("AMBp", 1)
            if len(parts) == 2:
                song_info = parts[1].strip().split(" by ")
                if len(song_info) == 2:
                    song_name, artist_name = song_info
                    if song_name != last_queued_song:
                        queue_song(song_name, artist_name)
                        last_queued_song = song_name
                        print("Queued Request Seen")
                    else:
                        print("Same song already queued, skipping...")

        if "AMBrn" in text_on_screen and ambnp_ready:
            if current_media_info:
                pyautogui.press('altleft')
                second_monitor_roblox_window.activate()
                print("Brought Roblox forward")
                time.sleep(1)
                pydirectinput.press('/')
                pyautogui.typewrite(message)
                pydirectinput.press('enter')
                pydirectinput.press("space")
                ambnp_ready = False

        if "AMBn" in text_on_screen:
            next_song_title, next_song_artist = get_next_song_in_queue()
            if next_song_title and next_song_artist:
                message = f"Next song in queue is {next_song_title} by {next_song_artist}\n"
                pyautogui.press('altleft')
                second_monitor_roblox_window.activate()
                time.sleep(1)
                pydirectinput.press('/')
                pyautogui.typewrite(message)
                pydirectinput.press('enter')
                pydirectinput.press("space")
            else:
                print("No song found in the queue or an error occurred.")

        time.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
