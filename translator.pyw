import keyboard
import pyperclip
import tkinter as tk
from deep_translator import GoogleTranslator
import threading
import time
import os
import sys
import ctypes
import ctypes.wintypes
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import configparser
import queue
import subprocess
import logging
import urllib.request
import urllib.parse
import json
import ssl

def translate_to_sinhala(text: str) -> str:
    """Translate text to Sinhala with Google client endpoints (dict-chrome-ex, gtx)
    which are immune to the HTTP 429 scraping block.
    """
    text = text.strip()
    if not text:
        return ""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    ctx = ssl.create_default_context()

    # Try official Chromium / Chrome extension endpoints first
    for client in ["dict-chrome-ex", "gtx"]:
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client={client}&sl=auto&tl=si&dt=t&q=" + urllib.parse.quote(text)
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                data = json.loads(response.read().decode("utf-8"))
                parts = [part[0] for part in data[0] if part and part[0]]
                res = "".join(parts).strip()
                if res:
                    return res
        except Exception as e:
            logging.warning("Translation with client '%s' failed: %s", client, e)

    # Fallback to deep_translator
    try:
        res = GoogleTranslator(source="auto", target="si").translate(text)
        if res and res.strip():
            return res.strip()
    except Exception as e:
        logging.warning("deep_translator fallback failed: %s", e)

    raise RuntimeError("Google Translate servers unreachable. Please check your internet connection.")

# ---------------------------------------------------------------------------
# Windows keystroke injection helpers (uses direct user32.keybd_event)
# keybd_event has no 64-bit struct padding issues and works reliably across all
# Windows versions without WinError 87 (ERROR_INVALID_PARAMETER).
# ---------------------------------------------------------------------------
KEYEVENTF_KEYUP = 0x0002

def send_ctrl_c():
    """Inject Ctrl+C reliably using user32.keybd_event."""
    user32 = ctypes.windll.user32
    user32.keybd_event(0x11, 0, 0, 0)                # Ctrl DOWN
    time.sleep(0.01)
    user32.keybd_event(0x43, 0, 0, 0)                # C DOWN
    time.sleep(0.01)
    user32.keybd_event(0x43, 0, KEYEVENTF_KEYUP, 0)  # C UP
    time.sleep(0.01)
    user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)  # Ctrl UP


# ---------------------------------------------------------------------------
# Admin elevation helpers
# ---------------------------------------------------------------------------
def is_admin():
    """Return True if the current process has Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def elevate():
    """Re-launch this process elevated via UAC and exit the current process."""
    if getattr(sys, 'frozen', False):
        prog = sys.executable
        params = ' '.join(f'"{a}"' for a in sys.argv[1:])
    else:
        prog = sys.executable
        script = os.path.abspath(sys.argv[0])
        rest = ' '.join(f'"{a}"' for a in sys.argv[1:])
        params = f'"{script}" {rest}'
    ctypes.windll.shell32.ShellExecuteW(None, 'runas', prog, params, None, 1)
    sys.exit(0)

def get_self_path():
    """Return the runnable path for this process (works in frozen EXE and source mode)."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(__file__)

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- 1. Config Logic ---
def get_config_path():
    exe_dir = os.path.dirname(get_self_path())
    return os.path.join(exe_dir, 'config.ini')

def get_shortcut():
    config = configparser.ConfigParser()
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            config.read(config_path, encoding='utf-8')
            val = config.get('Settings', 'hotkey', fallback='menu').strip().lower()
            if val:
                # Validate that keyboard library can parse the hotkey
                keyboard.parse_hotkey(val)
                return val
        except Exception as e:
            logging.warning("Config hotkey invalid (%s). Falling back to 'menu'", e)
            return 'menu'
    return 'menu'

def save_shortcut(hotkey):
    config = configparser.ConfigParser()
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            config.read(config_path, encoding='utf-8')
        except Exception:
            pass
    if not config.has_section('Settings'):
        config.add_section('Settings')
    config.set('Settings', 'hotkey', str(hotkey).strip().lower())
    with open(config_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

# --- 2. Settings GUI (Key Recorder) ---
def run_settings_gui():
    root = tk.Tk()
    root.title("Settings - Floating Translator")
    root.geometry("420x260")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    
    current_key = get_shortcut()
    
    title_lbl = tk.Label(root, text="Translation Shortcut Setup", font=("Segoe UI", 14, "bold"))
    title_lbl.pack(pady=12)

    status_lbl = tk.Label(root, text=f"Current Shortcut:  [ {current_key} ]", font=("Segoe UI", 11))
    status_lbl.pack(pady=6)

    info_lbl = tk.Label(root, text="Click 'Record New Shortcut' and press your desired key or combo\n(e.g., Menu, F1, or Ctrl+Shift+T)", font=("Segoe UI", 9), fg="#555555")
    info_lbl.pack(pady=4)

    def listen_for_shortcut():
        btn.config(text="Listening... Press your keys now!", state="disabled", bg="#fff3cd")
        root.update()
        
        try:
            new_shortcut = keyboard.read_hotkey(suppress=False)
        except Exception as e:
            logging.error("Failed to read hotkey: %s", e)
            new_shortcut = None
        
        if not new_shortcut or not str(new_shortcut).strip():
            status_lbl.config(text=f"No key detected. Keeping [ {current_key} ]", fg="red")
            btn.config(text="Record New Shortcut", state="normal", bg="SystemButtonFace", command=start_listening)
            return
            
        new_shortcut = str(new_shortcut).strip().lower()
        
        # Don't save lone modifier keys
        lone_modifiers = {'ctrl', 'alt', 'shift', 'windows', 'left ctrl', 'right ctrl', 'left alt', 'right alt', 'left shift', 'right shift'}
        if new_shortcut in lone_modifiers:
            status_lbl.config(text=f"Cannot use modifier '{new_shortcut}' alone.\nPlease combine it with another key.", fg="red")
            btn.config(text="Record New Shortcut", state="normal", bg="SystemButtonFace", command=start_listening)
            return
            
        try:
            keyboard.parse_hotkey(new_shortcut)
        except Exception as e:
            status_lbl.config(text=f"Invalid key combination: {e}", fg="red")
            btn.config(text="Record New Shortcut", state="normal", bg="SystemButtonFace", command=start_listening)
            return

        save_shortcut(new_shortcut)
        status_lbl.config(
            text=f"New Shortcut Saved:  [ {new_shortcut} ]\n\nClose this window to apply changes.",
            fg="green"
        )
        btn.config(text="Close & Apply", state="normal", bg="#d4edda", command=root.destroy)

    def start_listening():
        threading.Thread(target=listen_for_shortcut, daemon=True).start()

    btn = tk.Button(root, text="Record New Shortcut", font=("Segoe UI", 11), padx=10, pady=5, command=start_listening)
    btn.pack(pady=15)
    
    root.mainloop()

# --- 3. Main Application Logic ---
def main_app():
    log_path = os.path.join(os.path.dirname(get_self_path()), 'translator.log')
    logging.basicConfig(
        filename=log_path,
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(threadName)s — %(message)s',
        encoding='utf-8',
        force=True,
    )
    logging.info('main_app() started. Admin: %s', is_admin())

    hotkey = get_shortcut()
    logging.info('Translation hotkey: %s', hotkey)
    q = queue.Queue()
    root = tk.Tk()
    root.withdraw()
    _hook_handle = None

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
        """Launch the settings window in a separate process."""
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, '--setup']
        else:
            cmd = [sys.executable, get_self_path(), '--setup']
        logging.info('Launching settings subprocess: %s', cmd)
        subprocess.Popen(cmd)
        quit_app(icon, item)

    def quit_app(icon, item):
        nonlocal _hook_handle
        if _hook_handle:
            try:
                ctypes.windll.user32.UnhookWindowsHookEx(_hook_handle)
                logging.info('Unhooked native touchpad hook on exit')
            except Exception as e:
                logging.error('Error unhooking native touchpad hook: %s', e)
        icon.stop()
        root.destroy()
        sys.exit()

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

        pos_x = start_x + 15
        pos_y = start_y + 15

        if pos_x + win_width > screen_width:
            pos_x = start_x - win_width - 15

        if pos_y + win_height > screen_height:
            pos_y = start_y - win_height - 15
            
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
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            old_clipboard = ''

        # Allow user a moment to release trigger keys
        time.sleep(0.05)

        # Clear clipboard to detect fresh copy
        try:
            pyperclip.copy('')
        except Exception:
            pass

        time.sleep(0.02)
        # Inject Ctrl+C via user32.keybd_event
        send_ctrl_c()

        # Wait up to 500ms for clipboard to receive copied text
        selected_text = ''
        deadline = time.time() + 0.5
        while time.time() < deadline:
            time.sleep(0.03)
            try:
                candidate = pyperclip.paste()
                if candidate and candidate.strip():
                    selected_text = candidate
                    break
            except Exception:
                pass

        logging.debug('Clipboard captured (%d chars): %.80r', len(selected_text), selected_text)

        if selected_text and selected_text.strip():
            try:
                translation = translate_to_sinhala(selected_text)
                logging.info('Translated: %.80r -> %.80r', selected_text, translation)
                q.put(translation)
            except Exception as e:
                logging.error('Translation failed: %s', e, exc_info=True)
                q.put(f"Translation Error:\n{str(e)}")

        # Restore previous clipboard
        if old_clipboard:
            try:
                pyperclip.copy(old_clipboard)
            except Exception:
                pass

    def trigger():
        threading.Thread(target=get_translation, daemon=True, name='get_translation').start()

    # ---------------------------------------------------------------------------
    # Register translation hotkey with fallback
    # ---------------------------------------------------------------------------
    try:
        keyboard.add_hotkey(hotkey, trigger, suppress=True)
        logging.info("Registered translation hotkey: %s (suppress=True)", hotkey)
    except Exception as e:
        logging.error("Failed to register hotkey '%s': %s. Falling back to 'menu'", hotkey, e)
        try:
            keyboard.add_hotkey('menu', trigger, suppress=True)
            logging.info("Registered fallback translation hotkey: menu (suppress=True)")
        except Exception as e2:
            logging.error("Failed to register fallback hotkey 'menu': %s", e2)

    # Also register Ctrl+Shift+T as an alternate shortcut for laptops without a physical Menu key
    if str(hotkey).lower().strip() != 'ctrl+shift+t':
        try:
            keyboard.add_hotkey('ctrl+shift+t', trigger, suppress=True)
            logging.info("Registered alternate translation hotkey: ctrl+shift+t (suppress=True)")
        except Exception as e:
            logging.debug("Could not register alternate hotkey ctrl+shift+t: %s", e)

    # ---------------------------------------------------------------------------
    # WINDOWS TOUCHPAD GESTURE BUG FIX — NATIVE LOW-LEVEL KEYBOARD HOOK
    # ---------------------------------------------------------------------------
    # Intercepts touchpad gestures mapped to dummy keys and silently translates them:
    # ctrl+shift+f1 (or ctrl+f1)  →  alt+shift+esc   (cycle windows in reverse)
    # ctrl+shift+f2 (or ctrl+f2)  →  alt+esc         (cycle windows forward)
    #
    # Windows Precision Touchpad synthesizes keystrokes with scan_code=0 / injected.
    # A native WH_KEYBOARD_LL hook intercepts them at the Windows kernel message level,
    # releases modifier keys, injects the window switch, and suppresses raw F1/F2 keys
    # so they never leak into applications.
    # ---------------------------------------------------------------------------
    WH_KEYBOARD_LL = 13
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105

    VK_SHIFT = 0x10
    VK_CONTROL = 0x11
    VK_MENU = 0x12       # Alt
    VK_ESCAPE = 0x1B
    VK_F1 = 0x70
    VK_F2 = 0x71

    VK_LSHIFT = 0xA0
    VK_RSHIFT = 0xA1
    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3

    VK_MEDIA_NEXT_TRACK = 0xB0  # Next Track (176)
    VK_MEDIA_PREV_TRACK = 0xB1  # Previous Track (177)

    KEYEVENTF_KEYUP = 0x0002

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode", ctypes.wintypes.DWORD),
            ("scanCode", ctypes.wintypes.DWORD),
            ("flags", ctypes.wintypes.DWORD),
            ("time", ctypes.wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_size_t),
        ]

    HOOKPROC = ctypes.WINFUNCTYPE(
        ctypes.c_longlong,
        ctypes.c_int,
        ctypes.wintypes.WPARAM,
        ctypes.POINTER(KBDLLHOOKSTRUCT)
    )

    MAGIC_EXTRA_INFO = 0x54504144  # 'TPAD' signature to identify our injected keys

    def _is_desktop_or_shell(hwnd):
        if not hwnd or not ctypes.windll.user32.IsWindow(hwnd):
            return True
        class_buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, class_buf, 256)
        cls = class_buf.value
        return cls in ('Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd')

    def _send_alt_esc():
        user32 = ctypes.windll.user32
        # Release Ctrl and Shift first
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, MAGIC_EXTRA_INFO)
        user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, MAGIC_EXTRA_INFO)
        time.sleep(0.01)
        # Send Alt + Esc
        user32.keybd_event(VK_MENU, 0, 0, MAGIC_EXTRA_INFO)
        user32.keybd_event(VK_ESCAPE, 0, 0, MAGIC_EXTRA_INFO)
        time.sleep(0.02)
        user32.keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, MAGIC_EXTRA_INFO)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, MAGIC_EXTRA_INFO)

    def _send_alt_shift_esc():
        user32 = ctypes.windll.user32
        # Release Ctrl first
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, MAGIC_EXTRA_INFO)
        time.sleep(0.01)
        # Send Alt + Shift + Esc
        user32.keybd_event(VK_MENU, 0, 0, MAGIC_EXTRA_INFO)
        user32.keybd_event(VK_SHIFT, 0, 0, MAGIC_EXTRA_INFO)
        user32.keybd_event(VK_ESCAPE, 0, 0, MAGIC_EXTRA_INFO)
        time.sleep(0.02)
        user32.keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, MAGIC_EXTRA_INFO)
        user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, MAGIC_EXTRA_INFO)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, MAGIC_EXTRA_INFO)

    def _switch_window_forward():
        """Cycle windows forward (Alt + Esc), skipping desktop/taskbar so focus stays on apps."""
        def _send():
            try:
                _send_alt_esc()
                time.sleep(0.03)
                # If focus landed on Desktop/Taskbar, skip it immediately back to an application
                for _ in range(2):
                    fg = ctypes.windll.user32.GetForegroundWindow()
                    if not _is_desktop_or_shell(fg):
                        break
                    time.sleep(0.02)
                    _send_alt_esc()
                logging.info('Touchpad: Cycled window forward (Alt+Esc)')
            except Exception as e:
                logging.error('Error sending alt+esc: %s', e)
        threading.Thread(target=_send, daemon=True, name='touchpad-forward').start()

    def _switch_window_reverse():
        """Cycle windows in reverse (Alt + Shift + Esc), skipping desktop/taskbar so focus stays on apps."""
        def _send():
            try:
                _send_alt_shift_esc()
                time.sleep(0.03)
                # If focus landed on Desktop/Taskbar, skip it immediately back to an application
                for _ in range(2):
                    fg = ctypes.windll.user32.GetForegroundWindow()
                    if not _is_desktop_or_shell(fg):
                        break
                    time.sleep(0.02)
                    _send_alt_shift_esc()
                logging.info('Touchpad: Cycled window reverse (Alt+Shift+Esc)')
            except Exception as e:
                logging.error('Error sending alt+shift+esc: %s', e)
        threading.Thread(target=_send, daemon=True, name='touchpad-reverse').start()

    _touchpad_ctrl_down = False
    _touchpad_shift_down = False
    _last_touchpad_time = 0.0

    def _touchpad_lowlevel_proc(nCode, wParam, lParam):
        nonlocal _touchpad_ctrl_down, _touchpad_shift_down, _last_touchpad_time
        try:
            if nCode >= 0 and lParam:
                extra = lParam.contents.dwExtraInfo
                # Ignore keystrokes generated by our own app so they never corrupt modifier tracking
                if extra == MAGIC_EXTRA_INFO:
                    return ctypes.windll.user32.CallNextHookEx(None, nCode, wParam, lParam)

                vk = lParam.contents.vkCode
                flags = lParam.contents.flags
                scan = lParam.contents.scanCode
                is_down = (wParam in (WM_KEYDOWN, WM_SYSKEYDOWN))
                is_up = (wParam in (WM_KEYUP, WM_SYSKEYUP))

                # Track modifier keys from user or touchpad
                if vk in (VK_CONTROL, VK_LCONTROL, VK_RCONTROL):
                    _touchpad_ctrl_down = is_down
                elif vk in (VK_SHIFT, VK_LSHIFT, VK_RSHIFT):
                    _touchpad_shift_down = is_down

                user32 = ctypes.windll.user32
                ctrl_active = _touchpad_ctrl_down or bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)

                # Touchpad injects keys with scanCode=0 or LLKHF_INJECTED (flags & 0x10)
                is_injected = bool(flags & 0x10) or (scan == 0)

                # Mode 1: Custom shortcut gestures (Ctrl+Shift+F1 / Ctrl+Shift+F2)
                is_custom_f1 = (vk == VK_F1) and (ctrl_active or is_injected)
                is_custom_f2 = (vk == VK_F2) and (ctrl_active or is_injected)

                # Mode 2: System media gestures (Previous Track / Next Track)
                # Windows sends media keys globally to the session without UIPI restrictions,
                # allowing gestures to work EVEN when Administrator apps (Task Manager, Terminal) have focus!
                is_media_f1 = (vk == VK_MEDIA_PREV_TRACK) and is_injected
                is_media_f2 = (vk == VK_MEDIA_NEXT_TRACK) and is_injected

                is_gesture_f1 = is_custom_f1 or is_media_f1
                is_gesture_f2 = is_custom_f2 or is_media_f2

                if is_gesture_f1 or is_gesture_f2:
                    if is_down:
                        now = time.time()
                        if now - _last_touchpad_time > 0.05:  # 50ms debounce
                            _last_touchpad_time = now
                            if is_gesture_f1:
                                logging.info("Touchpad Hook: Intercepted reverse gesture (vk=0x%X) -> triggering reverse window switch", vk)
                                _switch_window_reverse()
                            else:
                                logging.info("Touchpad Hook: Intercepted forward gesture (vk=0x%X) -> triggering forward window switch", vk)
                                _switch_window_forward()
                    # Suppress raw key completely so active app / media player never receives it
                    return 1
        except Exception as e:
            logging.error("Touchpad hook procedure exception: %s", e)

        return ctypes.windll.user32.CallNextHookEx(None, nCode, wParam, lParam)

    # Register native low-level keyboard hook
    try:
        _c_hook_proc = HOOKPROC(_touchpad_lowlevel_proc)
        ctypes.windll.user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int, HOOKPROC, ctypes.wintypes.HINSTANCE, ctypes.wintypes.DWORD
        ]
        ctypes.windll.user32.SetWindowsHookExW.restype = ctypes.wintypes.HHOOK
        _hook_handle = ctypes.windll.user32.SetWindowsHookExW(WH_KEYBOARD_LL, _c_hook_proc, 0, 0)
        if _hook_handle:
            logging.info("Registered native Windows WH_KEYBOARD_LL hook for touchpad gestures (handle=%s)", _hook_handle)
        else:
            logging.error("Failed to install native hook: Windows error %s", ctypes.windll.kernel32.GetLastError())
    except Exception as e:
        logging.error("Exception setting up native touchpad hook: %s", e)

    # Also register keyboard library hotkeys as fallback
    try:
        keyboard.add_hotkey('ctrl+shift+f1', _switch_window_reverse, suppress=True)
        keyboard.add_hotkey('ctrl+shift+f2', _switch_window_forward, suppress=True)
        logging.info("Registered fallback touchpad hotkeys ctrl+shift+f1 and ctrl+shift+f2")
    except Exception as e:
        logging.debug("Could not register fallback touchpad hotkeys: %s", e)

    root.after(100, process_queue)
    root.mainloop()

# --- 4. Boot Logic ---
if __name__ == "__main__":
    # If launched with --setup, run the GUI and exit.
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        run_settings_gui()
        # After settings window closes, re-launch the background app.
        if getattr(sys, 'frozen', False):
            subprocess.Popen([sys.executable])
        else:
            subprocess.Popen([sys.executable, get_self_path()])
        sys.exit(0)

    # Ensure Administrator privileges before starting.
    # Global keyboard hooks must run at elevated integrity to intercept keys
    # from elevated windows (UIPI requirement).
    if not is_admin():
        logging.basicConfig(level=logging.DEBUG)
        logging.warning('Not running as Administrator — attempting UAC elevation.')
        elevate()
        ctypes.windll.user32.MessageBoxW(
            0,
            'Administrator privileges are required for global keyboard hooks to function.\n\n'
            'Please re-launch the application and accept the UAC prompt.',
            'Elevation Required',
            0x10,
        )
        sys.exit(1)

    try:
        main_app()
    except Exception as e:
        logging.critical('main_app() crashed: %s', e, exc_info=True)
        MB_RETRYCANCEL = 5
        MB_ICONERROR = 0x10
        IDRETRY = 4
        error_msg = (
            f'The Floating Sinhala Translator has crashed.\n'
            f'Error: {str(e)}\n\n'
            f'Do you want to relaunch the application?'
        )
        result = ctypes.windll.user32.MessageBoxW(
            0, error_msg, 'Application Crashed', MB_RETRYCANCEL | MB_ICONERROR
        )
        if result == IDRETRY:
            os.startfile(sys.executable)
        sys.exit(1)