# Floating Sinhala Translator

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](https://github.com/NimanthaShyamin/Floating-Cloud-Window-G-Translator)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Release-v1.1.0-brightgreen.svg)](https://github.com/NimanthaShyamin/Floating-Cloud-Window-G-Translator/releases)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Security](https://img.shields.io/badge/Code%20Signed-Authenticode%20SHA256-success.svg)](sign_build.ps1)

A lightweight, non-intrusive Windows desktop utility that translates selected text into **Sinhala** on demand. Results appear immediately in an elegant, auto-dismissing floating cloud tooltip right next to your mouse cursor.

The application also features a native low-level touchpad gesture remapper for frictionless window switching.

---

## ✨ Features

- **Instant Sinhala Translation**: Select text anywhere (browser, PDF, code editor, office documents), press your shortcut key, and get instant translation in a sleek dark floating cloud tooltip near the cursor.
- **Resilient Translation Engine**:
  - Leverages Google Translate client endpoints (`dict-chrome-ex`, `gtx`) immune to HTTP 429 scraping blocks.
  - Automatically falls back to `deep_translator` if primary endpoints are unreachable.
- **Customizable Global Shortcut**:
  - Default shortcut: `Menu` (Application key) or `Ctrl+Shift+T`.
  - Built-in interactive key recorder GUI to rebind any custom key or key combination.
- **Auto-Dismiss Floating Window**:
  - Rendered with high-readability Sinhala typography (`Iskoola Pota`).
  - Dismisses automatically on mouse movement, click, focus loss, or any keystroke so your workflow is never interrupted.
- **Native Touchpad Gesture Remapper**:
  - Intercepts touchpad horizontal swipe media events (Previous / Next Track) via native `WH_KEYBOARD_LL` low-level keyboard hooks.
  - Automatically converts gestures into fast window switching (`Alt + Esc` / `Alt + Shift + Esc`) while intelligently skipping desktop and taskbar surfaces.
  - Suppresses media key propagation to prevent accidental song skipping in media players.
- **Silent Boot without UAC Prompts**:
  - Automatically registers an elevated Windows Scheduled Task (`/SC ONLOGON /RL HIGHEST`) during installation.
  - Boots silently with Windows without nagging UAC popups every time you log in.
- **System Tray Integration**:
  - Runs unobtrusively in the background with minimal memory consumption.
  - Tray icon context menu allows changing shortcuts or exiting cleanly at any time.
- **Code Signed & Verified**:
  - Signed with SHA-256 / RSA-4096 Authenticode certificates and RFC 3161 timestamps.

---

## 🚀 Quick Start / Installation

### Method 1: Using the Installer (Recommended)

1. Download **`FloatingTranslator_Setup.exe`** from the [Releases](https://github.com/NimanthaShyamin/Floating-Cloud-Window-G-Translator/releases) section.
2. Run the setup installer and follow the wizard.
   - The installer automatically creates Start Menu and optional Desktop shortcuts.
   - Configures silent auto-start at Windows login via Windows Task Scheduler.
3. Upon completion, the setup launches the **Translation Shortcut Setup** window elevated so you can immediately configure your preferred shortcut.

> [!NOTE]
> Because the application relies on low-level global keyboard hooks to bypass Windows User Interface Privilege Isolation (UIPI), it must run with **Administrator privileges**. The installer configures this automatically.

### Method 2: Trusting the Self-Signed Certificate

If Windows SmartScreen warns about an unknown publisher:
1. Download `FloatingSinhalaTranslator_CodeSign.cer` from this repository.
2. Open an elevated PowerShell prompt (Run as Administrator) and run:
   ```powershell
   $cer = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("FloatingSinhalaTranslator_CodeSign.cer")
   $tp = New-Object System.Security.Cryptography.X509Certificates.X509Store("TrustedPublisher","LocalMachine")
   $tp.Open("ReadWrite"); $tp.Add($cer); $tp.Close()
   $rt = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root","LocalMachine")
   $rt.Open("ReadWrite"); $rt.Add($cer); $rt.Close()
   ```

---

## 🎯 Usage

### 1. Translating Text
1. Highlight any word, phrase, or sentence in any application.
2. Press your configured shortcut key (default: `Menu` key).
3. The Sinhala translation will pop up beside your cursor.
4. Move your mouse or click anywhere to dismiss the tooltip.

### 2. Changing the Shortcut
- Right-click the **Floating Sinhala Translator** icon in the Windows System Tray (notification area).
- Click **Change Shortcut**.
- Click **Record New Shortcut** and press your desired key or combination (e.g., `F1`, `Pause`, or `Ctrl+Shift+T`).
- Click **Close & Apply**.

### 3. Touchpad Window Switching
- **Swipe Right** (3-finger or 4-finger media swipe): Switch forward to previous active window.
- **Swipe Left**: Switch reverse to next active window.

---

## 🛠️ Building from Source

### Prerequisites
- Windows 10 or 11
- [Python 3.10+](https://www.python.org/)
- [Inno Setup 6 or 7](https://jrsoftware.org/isdl.php) (for building the installer)

### Step 1: Clone the Repository
```bash
git clone https://github.com/NimanthaShyamin/Floating-Cloud-Window-G-Translator.git
cd Floating-Cloud-Window-G-Translator
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run from Source
To test and run directly from Python:
```bash
pythonw translator.pyw
```

### Step 4: Compile Executable with PyInstaller
```bash
python -m PyInstaller "Floating Sinhala Translator.spec" --noconfirm
```
The compiled application will be generated in `dist\Floating Sinhala Translator\`.

### Step 5: Sign the Executable (Optional)
Run the automated code signing script in PowerShell:
```powershell
.\sign_build.ps1
```

### Step 6: Compile the Installer
Using the Inno Setup compiler (`ISCC.exe`):
```cmd
"C:\Program Files\Inno Setup 7\ISCC.exe" setup.iss
```
The final installer `FloatingTranslator_Setup.exe` will be located in the `Output\` folder.

---

## 📁 Project Structure

```text
├── Floating Sinhala Translator.spec       # PyInstaller bundle specification
├── FloatingSinhalaTranslator_CodeSign.cer # Public certificate for Authenticode trust
├── FloatingSinhalaTranslator_CodeSign.pfx # Certificate private key (for code signing)
├── app_icon.ico                           # Application & tray icon
├── requirements.txt                       # Python dependencies
├── setup.iss                              # Inno Setup installer script
├── sign_build.ps1                         # Automated certificate & binary signer
├── translator.pyw                         # Main application entry point & GUI
└── Output/                                # Compiled installer directory
```

---

## ⚙️ Configuration File (`config.ini`)

The application automatically creates and manages `config.ini` in its installation directory:

```ini
[Settings]
hotkey = menu
```

You can edit this file directly or use the built-in Settings recorder GUI.

---

## ❓ Troubleshooting & FAQ

<details>
<summary><strong>Why does the application require Administrator privileges?</strong></summary>

Windows User Interface Privilege Isolation (UIPI) prevents standard-level processes from capturing keyboard events and injecting keystrokes into windows running at elevated privileges (like Task Manager, elevated browsers, Command Prompt, or administrative utilities). Elevating the translator ensures hotkeys and touchpad gestures work reliably across every window on your system.
</details>

<details>
<summary><strong>Why do I not see a UAC prompt on computer startup?</strong></summary>

Rather than using basic `Run` registry keys (which trigger a UAC prompt upon login), the installer creates an elevated Scheduled Task (`/RL HIGHEST`). Windows Task Scheduler launches the application silently at user logon with full permissions.
</details>

<details>
<summary><strong>The Sinhala font characters look misaligned or boxy. How can I fix this?</strong></summary>

Windows has built-in support for Sinhala via the `Iskoola Pota` or `Nirmala UI` font. Ensure your Windows installation has the Sinhala Language Pack installed under **Windows Settings > Time & Language > Language & Region**.
</details>

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
Created and maintained by [Nimantha Shyamin](https://github.com/NimanthaShyamin).
