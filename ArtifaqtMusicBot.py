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
SPOTIPY_CLIENT_ID = '31528e8a540b445eb3f2799fc8591f66'
SPOTIPY_CLIENT_SECRET = '40c27d4c00474cbd9e0f4180633b0ce1'
SPOTIPY_REDIRECT_URI = 'http://localhost:25565'

# Function to retrieve media information
async def get_media_info():
    sessions = await MediaManager.request_async()
    current_session = sessions.get_current_session()
    if current_session:
        # TODO: Media player selection
        info = await current_session.try_get_media_properties_async()

        # Extract relevant information
        info_dict = {song_attr: getattr(info, song_attr) for song_attr in dir(info) if song_attr[0] != '_'}
        info_dict['genres'] = list(info_dict['genres'])

        pbinfo = current_session.get_playback_info()
        info_dict['status'] = pbinfo.playback_status

        return info_dict
    else:
        raise NoMediaRunningException("No media source running.")

# Function to perform OCR within the specified box
def perform_ocr():
    box = (2890, 307, 3240, 330)  # Define the box coordinates (top-left and bottom-right)
    screenshot = ImageGrab.grab(bbox=box, include_layered_windows=False, all_screens=True)  # Take a screenshot of the specified region
    text = pytesseract.image_to_string(screenshot)  # Perform OCR on the screenshot
    return text.strip()  # Return the extracted text after stripping whitespace

# Search song on Spotify and add to queue
def queue_song(song_name, artist_name=None):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                                   client_secret=SPOTIPY_CLIENT_SECRET,
                                                   redirect_uri=SPOTIPY_REDIRECT_URI,
                                                   scope="user-modify-playback-state"))

    # If artist name is provided, search for songs by that artist
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
    

    

def main():
    # Initialize pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Specify the Tesseract OCR executable path

    last_queued_song = None
    last_song_title = None
    last_song_artist = None
    ambnp_ready = None
    first_run = True

    while True:
        try:
            current_media_info = asyncio.run(get_media_info())  # Fetch currently playing song using media manager 
        except NoMediaRunningException:
            time.sleep(1.5)
            continue
        except Exception as e:
            print("!!!", e, traceback.format_exc())
            time.sleep(1.5)
            continue

        song_artist, song_title = (current_media_info['artist'], current_media_info['title'])
        # Perform OCR within the specified box
        text_on_screen = perform_ocr()
        print(f"Text within the box: {text_on_screen}")
        print(text_on_screen)

        # Check if the song has changed
        if song_title != last_song_title or song_artist != last_song_artist:
            # Store the current song as the last song
            last_song_title = song_title
            last_song_artist = song_artist
            ambnp_ready = True
            # Find the Roblox window on the second monitor
            roblox_windows = gw.getWindowsWithTitle("Roblox")
            second_monitor_roblox_window = next((window for window in roblox_windows if window.topleft[0] >= 1920), None)

            try:
                if second_monitor_roblox_window and (first_run or ambnp_ready):
                    pyautogui.press('altleft')  # Get that activation hotkey love :) (thank you Raymond Chen)
                    second_monitor_roblox_window.activate()
                    print("Brought Roblox forward")
                    time.sleep(1)


                # Simulate pressing the / key
                pydirectinput.press('/')
                # Type out the message
                message = f"Now playing {song_title} by {song_artist}\n"
                pyautogui.typewrite(message)
                # Simulate pressing the Enter key
                pydirectinput.press('enter')
                pydirectinput.press("space")
                first_run = False

            except gw.PyGetWindowException as e:
                print(f"Error occurred while activating Roblox window: {e}")

        # Check if "AMBp" is present in the recognized text
        if "AMBp" in text_on_screen:
            print("Found 'AMBp' to split and extract")
            # Split the text by "AMBp" to extract the song name and artist
            parts = text_on_screen.split("AMBp", 1)  # Split at the first occurrence of "AMBp"
            print("Parts after split: ", parts)
            
            # Ensure there are two parts (before and after "AMBp")
            if len(parts) == 2:
                # Extract song name and artist from the second part (after "AMBp")
                song_info = parts[1].strip().split(" by ")
                print(song_info)
                
                # Ensure there are exactly two parts (song name and artist)
                if len(song_info) == 2:
                    song_name, artist_name = song_info
                    print("Song name:", song_name)
                    print("Artist:", artist_name)
                    if song_name != last_queued_song:
                        queue_song(song_name, artist_name)
                        last_queued_song = song_name
                        print("Queued Request Seen")
                    else:
                        print("Same song already queued, skipping...")

        if "AMBnp" in text_on_screen and ambnp_ready == True:
                # Fetch current media info asynchronously
                current_media_info = asyncio.run(get_media_info())
                
                # If current_media_info is not None, proceed with sending the message
                if current_media_info:
                    pyautogui.press('altleft')  # Get that activation hotkey love :) (thank you Raymond Chen)
                    second_monitor_roblox_window.activate()
                    print("Brought Roblox forward")
                    time.sleep(1)  # Add a delay to ensure the window switch is complete
                    pydirectinput.press('/')
                    # Type out the message
                    pyautogui.typewrite(message)
                    # Simulate pressing the Enter key
                    pydirectinput.press('enter')
                    pydirectinput.press("space")
                
                    # Set the flag to True indicating AMBnp has been detected
                    ambnp_ready = False
        time.sleep(.5)  # Adjust the interval as needed

if __name__ == "__main__":
    main()
