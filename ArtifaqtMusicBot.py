import cv2
import numpy as np
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
from concurrent.futures import ThreadPoolExecutor

class NoMediaRunningException(Exception):
    pass

# Bot Commands
cmd_Play = 'AMBp'
cmd_Playing = 'AMBrn'
cmd_Next = 'AMBn'
cmd_Genre = 'AMBg'

# Spotify credentials
SPOTIPY_CLIENT_ID = ''
SPOTIPY_CLIENT_SECRET = ''
SPOTIPY_REDIRECT_URI = 'http://localhost:25565'
SCOPE = "user-read-playback-state user-modify-playback-state"

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope=SCOPE))

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
    try:
        box = (2890, 307, 3240, 330)
        screenshot = ImageGrab.grab(bbox=box, include_layered_windows=False, all_screens=True).convert('L')
        ret, screenshot = cv2.threshold(np.array(screenshot), 125, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(screenshot, config='--psm 7')
        return text.strip()
    except Exception as e:
        print(f"Error during OCR process: {e}")
        return ""

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
        track = results['tracks']['items'][0]
        song_name = track['name']
        sp.add_to_queue(uri=song_uri)
        print(f"Added '{song_name}' to Spotify queue.")
        return True, song_name
    else:
        print(f"Song '{song_name}' by '{artist_name}' not found on Spotify.")
        return False, None

# Function to queue a song from a specific genre on Spotify
def queue_song_by_genre(genre):
    try:
        recommendations = sp.recommendations(seed_genres=[genre], limit=1)
        if recommendations['tracks']:
            song = recommendations['tracks'][0]
            song_uri = song['uri']
            sp.add_to_queue(uri=song_uri)
            song_name = song['name']
            artist_name = song['artists'][0]['name']
            print(f"Added '{song_name}' by '{artist_name}' to Spotify queue.")
            return song_name, artist_name
        else:
            print(f"No recommendations found for genre '{genre}'.")
            return None, None
    except Exception as e:
        print(f"Error retrieving recommendations for genre '{genre}':", e)
        return None, None

# Function to activate the Roblox window
async def activate_roblox_window():
    roblox_windows = gw.getWindowsWithTitle("Roblox")
    second_monitor_roblox_window = next((window for window in roblox_windows if window.topleft[0] >= 1920), None)

    if second_monitor_roblox_window:
        try:
            pyautogui.press('altleft')
            second_monitor_roblox_window.activate()
            print("Brought Roblox forward")
            await asyncio.sleep(1)
            return second_monitor_roblox_window
        except gw.PyGetWindowException as e:
            print(f"Error occurred while activating Roblox window: {e}")
    else:
        print("Roblox window not found on the second monitor.")
    return None

# Function to get the most recent queued track
def get_most_recent_queued_track():
    try:
        queue = sp.queue()
        queue_tracks = queue['queue']
        
        if queue_tracks:
            most_recent_track = queue_tracks[-1]  # Get the last track in the queue
            track_name = most_recent_track['name']
            track_artists = ', '.join(artist['name'] for artist in most_recent_track['artists'])
            return track_name, track_artists
        else:
            return None, None
        
    except spotipy.SpotifyException as e:
        print(f"Error retrieving queue: {e}")

# Main function
async def main():
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    last_queued_song = None
    last_song_title = None
    last_song_artist = None

    with ThreadPoolExecutor(max_workers=5) as executor:
        while True:
            try:
                current_media_info = await get_media_info()
            except NoMediaRunningException:
                await asyncio.sleep(1.5)
                continue
            except Exception as e:
                print("!!!", e, traceback.format_exc())
                await asyncio.sleep(1.5)
                continue

            song_artist, song_title = (current_media_info['artist'], current_media_info['title'])
            text_on_screen = await asyncio.get_event_loop().run_in_executor(executor, perform_ocr)
            print(f"Text within the box: {text_on_screen}")

            if song_title != last_song_title or song_artist != last_song_artist:
                last_song_title = song_title
                last_song_artist = song_artist

                roblox_window = await activate_roblox_window()
                if roblox_window:
                    try:
                        message = f"Now playing: {song_title} by {song_artist}\n"
                        pydirectinput.press('/')
                        pyautogui.typewrite(message)
                        pydirectinput.press('enter')
                        pydirectinput.press("space")
                    except gw.PyGetWindowException as e:
                        print(f"Error occurred while typing in Roblox window: {e}")

            if cmd_Play in text_on_screen:
                print("Found 'AMBp' to split and extract")
                parts = text_on_screen.split("AMBp", 1)
                if len(parts) == 2:
                    song_info = parts[1].strip().split(" by ")
                    if len(song_info) == 2:
                        song_name, artist_name = song_info
                        if song_name != last_queued_song:
                            success, track_name = await asyncio.get_event_loop().run_in_executor(executor, queue_song, song_name, artist_name)
                            if success:
                                last_queued_song = song_name
                                await asyncio.sleep(.2)
                                message = f"Queued: {track_name}!"
                                roblox_window = await activate_roblox_window()
                                if roblox_window:
                                    try:
                                        pydirectinput.press('/')
                                        pyautogui.typewrite(message)
                                        pydirectinput.press('enter')
                                        pydirectinput.press("space")
                                    except gw.PyGetWindowException as e:
                                        print(f"Error occurred while typing in Roblox window: {e}")
                                print("Queued Request Seen")
                            else:
                                print(f"Failed to queue the song: {song_name} by {artist_name}")
                                message = f"Error queuing the song, please try again!"
                                roblox_window = await activate_roblox_window()
                                if roblox_window:
                                    try:
                                        pydirectinput.press('/')
                                        pyautogui.typewrite(message)
                                        pydirectinput.press('enter')
                                        pydirectinput.press('space')
                                    except gw.PyGetWindowException as e:
                                        print(f"Error occurred while typing in Roblox window: {e}")
                        else:
                            print("Same song already queued, skipping...")

            if cmd_Playing in text_on_screen:
                print("Found 'AMBrn' on screen!")
                if current_media_info:
                    roblox_window = await activate_roblox_window()
                    if roblox_window:
                        try:
                            message = f"Now playing: {current_media_info['title']} by {current_media_info['artist']}\n"
                            pydirectinput.press('/')
                            pyautogui.typewrite(message)
                            pydirectinput.press('enter')
                            pydirectinput.press("space")
                        except gw.PyGetWindowException as e:
                            print(f"Error occurred while typing in Roblox window: {e}")

            if cmd_Next in text_on_screen:
                print("Found 'AMBn' on screen!")
                next_song_title, next_song_artist = await asyncio.get_event_loop().run_in_executor(executor, get_next_song_in_queue)
                if next_song_title and next_song_artist:
                    message = f"Next song in queue is: {next_song_title} by {next_song_artist}\n"
                    roblox_window = await activate_roblox_window()
                    if roblox_window:
                        try:
                            pydirectinput.press('/')
                            pyautogui.typewrite(message)
                            pydirectinput.press('enter')
                            pydirectinput.press("space")
                        except gw.PyGetWindowException as e:
                            print(f"Error occurred while typing in Roblox window: {e}")
                else:
                    print("Queue is empty. No next song to announce.")

            if cmd_Genre in text_on_screen:
                print("Found 'AMBg' to queue a song of a specific genre")
                parts = text_on_screen.split("AMBg", 1)
                if len(parts) == 2:
                    genre = parts[1].strip()
                    if genre:
                        song_name, artist_name = await asyncio.get_event_loop().run_in_executor(executor, queue_song_by_genre, genre)
                        if song_name and artist_name:
                            message = f"A random '{genre}' song added!\n"
                            roblox_window = await activate_roblox_window()
                            if roblox_window:
                                try:
                                    pydirectinput.press('/')
                                    pyautogui.typewrite(message)
                                    pydirectinput.press('enter')
                                    pydirectinput.press("space")
                                except gw.PyGetWindowException as e:
                                    print(f"Error occurred while typing in Roblox window: {e}")

            await asyncio.sleep(0.2)

if __name__ == "__main__":
    asyncio.run(main())
