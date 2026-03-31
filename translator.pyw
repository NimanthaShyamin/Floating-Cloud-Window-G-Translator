import keyboard
import pyperclip
import tkinter as tk
from deep_translator import GoogleTranslator
import threading
import time
import os
import winreg as reg

# --- 1. Startup Logic ---
def add_to_startup():
    pth = os.path.realpath(__file__)
    address = r'Software\Microsoft\Windows\CurrentVersion\Run'
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, address, 0, reg.KEY_SET_VALUE)
        reg.SetValueEx(key, "MyTranslationTool", 0, reg.REG_SZ, f'pythonw.exe "{pth}"')
        reg.CloseKey(key)
    except Exception as e:
        pass

# --- 2. Translation Logic ---
def get_translation():
    old_clipboard = pyperclip.paste()
    keyboard.press_and_release('ctrl+c')
    time.sleep(0.15) 
    
    selected_text = pyperclip.paste()
    
    if selected_text.strip():
        try:
            translation = GoogleTranslator(source='auto', target='si').translate(selected_text)
            show_floating_window(translation)
        except Exception as e:
            print(f"Error: {e}")
    
    pyperclip.copy(old_clipboard)

def show_floating_window(text):
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    
    # --- Rounded Corners ---
    # We set the main window to a weird color, and tell Windows to make that color invisible!
    TRANSPARENT_COLOR = '#abcdef'
    root.configure(bg=TRANSPARENT_COLOR)
    root.attributes("-transparentcolor", TRANSPARENT_COLOR)
    
    # Create a canvas to draw our custom cloud shape
    canvas = tk.Canvas(root, bg=TRANSPARENT_COLOR, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    
    # Draw the text first so we know how big to make the box
    padding = 20
    text_id = canvas.create_text(padding, padding, text=text, 
                                 font=("Iskoola Pota", 14, "bold"), 
                                 fill="#00ff00", width=350, anchor="nw")
    
    # Calculate the size needed for the window based on the text
    bbox = canvas.bbox(text_id)
    win_width = bbox[2] + padding
    win_height = bbox[3] + padding
    canvas.config(width=win_width, height=win_height)
    
    # Function to draw a smooth rounded rectangle
    def round_rectangle(x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1,
                  x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius,
                  x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2,
                  x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    # Draw the black rounded background with a thin green border
    rect_id = round_rectangle(2, 2, win_width-2, win_height-2, radius=20, 
                              fill="#111111", outline="#00ff00", width=2)
    
    # Push the background behind the text
    canvas.tag_lower(rect_id, text_id)

    # Position at mouse cursor
    start_x, start_y = root.winfo_pointerxy()
    root.geometry(f"{win_width}x{win_height}+{start_x+15}+{start_y+15}")

    def close_app(event=None):
        root.destroy()

    # Check for global mouse movement to close it
    def check_mouse_movement():
        try:
            current_x, current_y = root.winfo_pointerxy()
            if abs(current_x - start_x) > 20 or abs(current_y - start_y) > 20:
                close_app()
            else:
                root.after(100, check_mouse_movement)
        except tk.TclError:
            pass

    check_mouse_movement()

    root.bind("<FocusOut>", close_app)
    root.bind("<Button-1>", close_app)
    root.bind("<Key>", close_app)

    root.focus_force()
    root.mainloop()

def trigger():
    threading.Thread(target=get_translation).start()

# --- 3. Main Execution ---
if __name__ == "__main__":
    add_to_startup() 
    keyboard.add_hotkey('menu', trigger, suppress=True)
    keyboard.wait()
