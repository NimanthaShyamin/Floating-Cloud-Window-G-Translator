import keyboard
import pyperclip
import tkinter as tk
from deep_translator import GoogleTranslator
import threading
import time
import os
import sys
import ctypes
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import configparser
import queue
import subprocess

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- 1. Config Logic ---
def get_config_path():
    exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
    return os.path.join(exe_dir, 'config.ini')

def get_shortcut():
    config = configparser.ConfigParser()
    config_path = get_config_path()
    if os.path.exists(config_path):
        config.read(config_path)
        return config.get('Settings', 'hotkey', fallback='menu')
    return 'menu' # Default fallback

def save_shortcut(hotkey):
    config = configparser.ConfigParser()
    config_path = get_config_path()
    if os.path.exists(config_path):
        config.read(config_path)
    if not config.has_section('Settings'):
        config.add_section('Settings')
    config.set('Settings', 'hotkey', hotkey)
    with open(config_path, 'w') as configfile:
        config.write(configfile)

# --- 2. Settings GUI (The Key Recorder) ---
def run_settings_gui():
    root = tk.Tk()
    root.title("Settings - Floating Translator")
    root.geometry("400x250")
    root.attributes("-topmost", True)
    
    current_key = get_shortcut()
    
    title_lbl = tk.Label(root, text="Translation Shortcut Setup", font=("Arial", 14, "bold"))
    title_lbl.pack(pady=10)

    status_lbl = tk.Label(root, text=f"Current Shortcut:  [ {current_key} ]", font=("Arial", 11))
    status_lbl.pack(pady=10)

    def listen_for_shortcut():
        btn.config(text="Listening... Press your keys now!", state="disabled", bg="yellow")
        root.update()
        
        # This records the exact physical keys pressed!
        new_shortcut = keyboard.read_hotkey(suppress=False)
        save_shortcut(new_shortcut)
        
        status_lbl.config(text=f"New Shortcut Saved:  [ {new_shortcut} ]\n\n(App will restart automatically when you close this window)", fg="green")
        btn.config(text="Close & Restart App", state="normal", bg="lightgray", command=root.destroy)

    def start_listening():
        threading.Thread(target=listen_for_shortcut, daemon=True).start()

    btn = tk.Button(root, text="Record New Shortcut", font=("Arial", 12), command=start_listening)
    btn.pack(pady=15)
    
    root.mainloop()

# --- 3. Main Application Logic ---
def main_app():
    hotkey = get_shortcut()
    q = queue.Queue() 
    root = tk.Tk()
    root.withdraw()

    # System Tray Icon
    def create_tray_image():
        icon_path = resource_path('app_icon.ico')
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        else:
            image = Image.new('RGB', (64, 64), color=(20, 20, 20))
            d = ImageDraw.Draw(image)
            d.text((15, 20), "SI", fill=(0, 255, 0))
            return image

    def open_settings(icon, item):
        # Open the settings window as a separate process so it doesn't crash the tray
        subprocess.Popen([sys.executable, "--setup"])
        quit_app(icon, item) # Close current background app so the new shortcut can take effect

    def quit_app(icon, item):
        icon.stop()
        root.destroy()
        sys.exit()

    # Add Settings to the right-click menu!
    menu = pystray.Menu(
        item('Change Shortcut', open_settings),
        item('Exit', quit_app)
    )
    tray_icon = pystray.Icon("FloatingTranslator", create_tray_image(), "Floating Sinhala Translator", menu=menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()

    # Floating Window Logic
    def show_floating_window(text):
        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        
        TRANSPARENT_COLOR = '#abcdef'
        win.configure(bg=TRANSPARENT_COLOR)
        win.attributes("-transparentcolor", TRANSPARENT_COLOR)
        
        canvas = tk.Canvas(win, bg=TRANSPARENT_COLOR, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        padding = 20
        text_id = canvas.create_text(padding, padding, text=text, font=("Iskoola Pota", 14, "bold"), fill="#ffffff", width=350, anchor="nw")
        
        bbox = canvas.bbox(text_id)
        win_width = bbox[2] + padding
        win_height = bbox[3] + padding
        canvas.config(width=win_width, height=win_height)
        
        def round_rectangle(x1, y1, x2, y2, radius=25, **kwargs):
            points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
            return canvas.create_polygon(points, **kwargs, smooth=True)

        rect_id = round_rectangle(2, 2, win_width-2, win_height-2, radius=20, fill="#000000", outline="#ffffff", width=2)
        canvas.tag_lower(rect_id, text_id)

        start_x, start_y = win.winfo_pointerxy()
        screen_width = win.winfo_screenwidth()
        screen_height = win.winfo_screenheight()

        # Default position (bottom-right of cursor)
        pos_x = start_x + 15
        pos_y = start_y + 15

        # If it goes off the right edge, flip it to the left side of the cursor
        if pos_x + win_width > screen_width:
            pos_x = start_x - win_width - 15

        # If it goes off the bottom edge, flip it above the cursor
        if pos_y + win_height > screen_height:
            pos_y = start_y - win_height - 15
            
        # Extra safety: Ensure it never goes off the top or left edges either
        pos_x = max(0, pos_x)
        pos_y = max(0, pos_y)

        win.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")

        def close_app(event=None):
            win.destroy()

        def check_mouse_movement():
            try:
                current_x, current_y = win.winfo_pointerxy()
                if abs(current_x - start_x) > 20 or abs(current_y - start_y) > 20:
                    close_app()
                else:
                    win.after(100, check_mouse_movement)
            except tk.TclError:
                pass

        check_mouse_movement()
        win.bind("<FocusOut>", close_app)
        win.bind("<Button-1>", close_app)
        win.bind("<Key>", close_app)
        win.focus_force()

    def process_queue():
        try:
            text = q.get_nowait()
            show_floating_window(text)
        except queue.Empty:
            pass
        root.after(100, process_queue)

    def get_translation():
        old_clipboard = pyperclip.paste()
        keyboard.press_and_release('ctrl+c')
        time.sleep(0.15) 
        selected_text = pyperclip.paste()
        if selected_text.strip():
            try:
                translation = GoogleTranslator(source='auto', target='si').translate(selected_text)
                q.put(translation)
            except Exception as e:
                pass
        pyperclip.copy(old_clipboard)

    def trigger():
        threading.Thread(target=get_translation, daemon=True).start()

    keyboard.add_hotkey(hotkey, trigger, suppress=True)

    root.after(100, process_queue)
    root.mainloop()

# --- 4. Boot Logic ---
if __name__ == "__main__":
    # If launched with --setup, run the GUI and exit.
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        run_settings_gui()
        # After settings window closes, launch the background app normally!
        subprocess.Popen([sys.executable])
        sys.exit(0)
        
    try:
        main_app()
    except Exception as e:
        MB_RETRYCANCEL = 5
        MB_ICONERROR = 0x10
        IDCANCEL = 2
        IDRETRY = 4
        error_msg = f"The Floating Sinhala Translator has crashed.\nError: {str(e)}\n\nDo you want to relaunch the application?"
        result = ctypes.windll.user32.MessageBoxW(0, error_msg, "Application Crashed", MB_RETRYCANCEL | MB_ICONERROR)
        if result == IDRETRY:
            os.startfile(sys.executable)
        sys.exit(1)