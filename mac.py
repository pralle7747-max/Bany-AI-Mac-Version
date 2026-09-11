import os
import sys
import sqlite3
import threading
import re
import time
import math
import colorsys
import uuid
import json
import base64
import subprocess
import webbrowser
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import customtkinter as ctk
import pyttsx3
import requests
from duckduckgo_search import DDGS
from google import genai
from google.genai import types
import urllib.request
import urllib.error

# --- UPDATE-HANDLER ---
if "--apply-update" in sys.argv:
    time.sleep(2)
    if len(sys.argv) > 2:
        target_exe = sys.argv[2]
        new_exe = target_exe + ".new"
        if os.path.exists(new_exe):
            try:
                os.replace(new_exe, target_exe)
            except Exception:
                pass
        subprocess.Popen([target_exe])
    sys.exit(0)

# --- FIREBASE EINGEBAUT ---
import firebase_admin
from firebase_admin import credentials, db

def decode_key(encoded_str: str) -> str:
    if not encoded_str or encoded_str.startswith("DEIN_"):
        return encoded_str
    try:
        return base64.b64decode(encoded_str.encode('utf-8')).decode('utf-8')
    except Exception:
        return encoded_str

RAW_GEMINI_KEY = "QVEuQWI4Uk42THYzR09JbjN2Z0xBLUFidUU5NVkyYVhTaEZlcFFaNmRiMHo2ZTFjRlZTbmc=" 
RAW_DISCORD_WEBHOOK = "aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTU0Nzc1NDE3NzQ3NDYwMTA5MS9lT05ndVBFei1zNFBxeGJYY0pkTFE0SFltOG9aY0NyblR4MkticVFKRTE1QUVjMEgtS05mNEZwRm1BcjdYcGtuVVYyNg=="

GEMINI_API_KEY = decode_key(RAW_GEMINI_KEY)
DISCORD_WEBHOOK_URL = decode_key(RAW_DISCORD_WEBHOOK)

UPDATE_URL = "https://raw.githubusercontent.com/pralle7747-max/Bany-AI/main/version.json"
CURRENT_VERSION = "3.0.0"
SYSTEM_PROMPT_FILE = "system_prompt.txt"
SETTINGS_FILE = "settings.json"
FIREBASE_KEY_FILE = "serviceAccountKey.json"
FIREBASE_DB_URL = "https://bany-ai-default-rtdb.europe-west1.firebasedatabase.app/"
DISCORD_INVITE_URL = "https://discord.gg/8zPbwgDHwV"

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def init_firebase():
    key_path = get_resource_path(FIREBASE_KEY_FILE)
    if os.path.exists(key_path):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
            return db.reference('knowledge')
        except Exception as e:
            print(f"Firebase Fehler: {e}")
            return None
    return None

firebase_ref = init_firebase()

def clean_firebase_key(text: str) -> str:
    return text.lower().strip().replace('.', '_').replace('#', '_').replace('$', '_').replace('[', '_').replace(']', '_')

def get_firebase_answer(frage: str):
    if not firebase_ref:
        return None
    try:
        key = clean_firebase_key(frage)
        data = firebase_ref.child(key).get()
        if data and isinstance(data, dict):
            return data.get("antwort")
    except Exception:
        pass
    return None

def save_firebase_answer(frage: str, antwort: str):
    if not firebase_ref:
        return
    try:
        key = clean_firebase_key(frage)
        firebase_ref.child(key).set({"frage_original": frage, "antwort": antwort})
    except Exception:
        pass

def setup_system_prompt():
    prompt_path = get_resource_path(SYSTEM_PROMPT_FILE)
    if not os.path.exists(prompt_path):
        default_prompt = (
            "Du bist ein intelligenter, freundlicher und hilfsbereiter KI-Assistent namens Bany AI im macOS-Design. "
            "Antworte stets präzise, gut strukturiert und höflich auf Deutsch."
        )
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(default_prompt)

def load_system_prompt():
    setup_system_prompt()
    try:
        with open(get_resource_path(SYSTEM_PROMPT_FILE), "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "Du bist Bany AI, ein hilfreicher KI-Assistent."

# --- AUTO-UPDATE ---
def check_and_apply_update():
    if "DEIN_USER" in UPDATE_URL or not UPDATE_URL.startswith("http"):
        return
    try:
        req = urllib.request.Request(UPDATE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
        if data.get("version") and data.get("version") != CURRENT_VERSION:
            download_and_apply_update(data.get("url"))
    except Exception:
        pass

def download_and_apply_update(url):
    try:
        real_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        new_path = real_path + ".new"
        urllib.request.urlretrieve(url, new_path)
        subprocess.Popen([real_path, "--apply-update", real_path])
        sys.exit(0)
    except Exception:
        pass

threading.Thread(target=check_and_apply_update, daemon=True).start()

# --- THEMES & GLASS CONFIG ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

THEMES = {
    "macOS Liquid 🍋": {"bg": "#1e1e1e", "sidebar_bg": "#262626", "accent": "#0a84ff", "text": "#ffffff", "card": "#2d2d2d"},
    "Sonoma Dark": {"bg": "#121212", "sidebar_bg": "#1a1a1a", "accent": "#ff9f0a", "text": "#ffffff", "card": "#222222"},
    "Sequoia Silver": {"bg": "#2c2c2e", "sidebar_bg": "#1c1c1e", "accent": "#32d74b", "text": "#ffffff", "card": "#3a3a3c"}
}

LIVE_WALLPAPERS = [
    "macOS Sequoia Aurora", "Cyberpunk Neon Rain", "Deep Ocean Blue", 
    "Sunset Orange Glow", "Matrix Green Stream", "Minimalist Gray Mist", 
    "Midnight Purple Void", "Golden Desert Mirage", "Frosty Arctic Wave", "Dynamic Citrus Lemon"
]

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("ki_gedaechtnis.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS anfragen (id INTEGER PRIMARY KEY AUTOINCREMENT, frage TEXT NOT NULL, antwort TEXT NOT NULL, status TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, is_pinned INTEGER DEFAULT 0)")
    try:
        cursor.execute("ALTER TABLE chats ADD COLUMN is_pinned INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def save_chat_message(chat_id, role, content):
    conn = sqlite3.connect("ki_gedaechtnis.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_pinned FROM chats WHERE chat_id = ? LIMIT 1", (chat_id,))
    row = cursor.fetchone()
    is_pinned = row[0] if row else 0
    cursor.execute("INSERT INTO chats (chat_id, role, content, is_pinned) VALUES (?, ?, ?, ?)", (chat_id, role, content, is_pinned))
    conn.commit()
    conn.close()

def load_chat_history(chat_id):
    conn = sqlite3.connect("ki_gedaechtnis.db")
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chats WHERE chat_id = ? ORDER BY id ASC", (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return [types.Content(role=role, parts=[types.Part.from_text(text=content)]) for role, content in rows]

def get_all_chat_sessions():
    conn = sqlite3.connect("ki_gedaechtnis.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, content, timestamp, MAX(is_pinned) as pinned FROM chats WHERE role = 'user' GROUP BY chat_id ORDER BY pinned DESC, MAX(id) DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def toggle_pin_chat(chat_id):
    conn = sqlite3.connect("ki_gedaechtnis.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_pinned FROM chats WHERE chat_id = ? LIMIT 1", (chat_id,))
    row = cursor.fetchone()
    if row:
        new_status = 0 if row[0] == 1 else 1
        cursor.execute("UPDATE chats SET is_pinned = ? WHERE chat_id = ?", (new_status, chat_id))
        conn.commit()
    conn.close()

def delete_chat_session(chat_id):
    conn = sqlite3.connect("ki_gedaechtnis.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

init_db()

# --- SPLASHSCREEN (macOS Style) ---
class MacSplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        w, h = 500, 300
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg="#1e1e1e")

        frame = tk.Frame(self, bg="#1e1e1e")
        frame.pack(expand=True, fill="both")

        tk.Label(frame, text="🍏", font=("Helvetica", 50), fg="white", bg="#1e1e1e").pack(pady=(50, 10))
        tk.Label(frame, text="Bany AI for macOS", font=("SF Pro Display", 22, "bold"), fg="white", bg="#1e1e1e").pack()
        tk.Label(frame, text="Loading Live Wallpaper & Glass Engine...", font=("SF Pro Text", 11), fg="#888888", bg="#1e1e1e").pack(pady=(5, 0))

        self.start_time = time.time()
        self.fade_in()

    def fade_in(self):
        if time.time() - self.start_time < 2.5:
            self.after(100, self.fade_in)
        else:
            self.destroy()
            self.master.deiconify()

# --- HAUPTANWENDUNG ---
class AetherOSAssistant(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title(f"Bany AI (v{CURRENT_VERSION}) - macOS Edition")
        self.geometry("1150x780")
        self.minsize(950, 650)

        self.api_key = GEMINI_API_KEY
        if not self.api_key or self.api_key.startswith("DEIN_"):
            self.api_key = simpledialog.askstring("Gemini API Key", "Bitte gib deinen Gemini API-Key ein:", show='*')

        if not self.api_key:
            messagebox.showerror("Fehler", "Ohne API-Key kann Bany AI nicht gestartet werden.")
            self.destroy()
            return

        self.client = genai.Client(api_key=self.api_key)
        self.current_chat_id = str(uuid.uuid4())
        self.is_admin_logged_in = False
        self.anim_step = 0

        # Einstellungen Variablen
        self.animated_mode = tk.BooleanVar(value=True)
        self.glass_mode = tk.BooleanVar(value=True)
        self.tts_enabled = tk.BooleanVar(value=False)
        self.tts_volume = 1.0
        self.current_theme_name = "macOS Liquid 🍋"
        self.current_theme = THEMES[self.current_theme_name]
        self.current_wallpaper = "macOS Sequoia Aurora"
        self.current_font_size = 14

        self.load_settings()
        self.setup_ui()
        self.apply_theme(self.current_theme_name)

        self.after(50, self.animate_live_background)
        MacSplashScreen(self)

    def load_settings(self):
        settings_path = get_resource_path(SETTINGS_FILE)
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.animated_mode.set(data.get("animated_mode", True))
                    self.glass_mode.set(data.get("glass_mode", True))
                    self.tts_enabled.set(data.get("tts_enabled", False))
                    self.tts_volume = data.get("tts_volume", 1.0)
                    self.current_theme_name = data.get("theme_name", "macOS Liquid 🍋")
                    if self.current_theme_name in THEMES:
                        self.current_theme = THEMES[self.current_theme_name]
                    self.current_wallpaper = data.get("wallpaper", "macOS Sequoia Aurora")
                    self.current_font_size = data.get("font_size", 14)
            except Exception:
                pass

    def save_settings(self):
        data = {
            "animated_mode": self.animated_mode.get(),
            "glass_mode": self.glass_mode.get(),
            "tts_enabled": self.tts_enabled.get(),
            "tts_volume": self.tts_volume,
            "theme_name": self.current_theme_name,
            "wallpaper": self.current_wallpaper,
            "font_size": self.current_font_size
        }
        try:
            with open(get_resource_path(SETTINGS_FILE), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Hintergrund Canvas für Live Wallpaper
        self.bg_canvas = tk.Canvas(self, highlightthickness=0, bg="#1e1e1e")
        self.bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        # macOS Sidebar (Glass Panel Look)
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#262626" if not self.glass_mode.get() else "#1a1a1a")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        # macOS Window Control Dots oben links
        dots_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        dots_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        for color in ["#ff5f56", "#ffbd2e", "#27c93f"]:
            lbl = tk.Label(dots_frame, text="●", fg=color, bg=self.sidebar_frame.cget("fg_color"), font=("Helvetica", 14))
            lbl.pack(side="left", padx=2)

        brand_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_frame.grid(row=1, column=0, padx=15, pady=(5, 10), sticky="w")
        self.logo_label = ctk.CTkLabel(brand_frame, text="🍏 BanyAI", font=("SF Pro Display", 16, "bold"), text_color="#0a84ff")
        self.logo_label.pack(side="left")

        self.btn_new_chat = ctk.CTkButton(self.sidebar_frame, text="➕  Neuer Chat", anchor="w", fg_color="transparent", text_color="#ffffff", hover_color="#3a3a3c", font=("SF Pro Text", 13), command=self.start_new_chat)
        self.btn_new_chat.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        self.btn_search_chat = ctk.CTkButton(self.sidebar_frame, text="🔍  Chats durchsuchen", anchor="w", fg_color="transparent", text_color="#ffffff", hover_color="#3a3a3c", font=("SF Pro Text", 13), command=self.search_chats_dialog)
        self.btn_search_chat.grid(row=3, column=0, sticky="ew", padx=10, pady=2)

        self.btn_discord = ctk.CTkButton(self.sidebar_frame, text="💬  Discord Community", anchor="w", fg_color="transparent", text_color="#0a84ff", hover_color="#3a3a3c", font=("SF Pro Text", 13, "bold"), command=lambda: webbrowser.open(DISCORD_INVITE_URL))
        self.btn_discord.grid(row=4, column=0, sticky="ew", padx=10, pady=2)

        for idx, (name, cmd) in enumerate([("🖼️  Bilder (Soon)", lambda: self.show_soon("Bilder")), ("📦  Mediathek (Soon)", lambda: self.show_soon("Mediathek")), ("✂️  KI CUT (Soon)", lambda: self.show_soon("KI CUT"))], start=5):
            btn = ctk.CTkButton(self.sidebar_frame, text=name, anchor="w", fg_color="transparent", text_color="#666666", hover_color="#3a3a3c", font=("SF Pro Text", 13), command=cmd)
            btn.grid(row=idx, column=0, sticky="ew", padx=10, pady=2)

        self.lbl_history_header = ctk.CTkLabel(self.sidebar_frame, text="Verlauf", font=("SF Pro Text", 11, "bold"), text_color="#888888", anchor="w")
        self.lbl_history_header.grid(row=8, column=0, sticky="w", padx=15, pady=(15, 2))

        self.scroll_history = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.scroll_history.grid(row=9, column=0, sticky="nsew", padx=5, pady=(2, 2))
        self.scroll_history.grid_columnconfigure(0, weight=1)

        bottom_menu = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        bottom_menu.grid(row=10, column=0, sticky="ew", padx=10, pady=(5, 10))

        ctk.CTkButton(bottom_menu, text="💾  Exportieren", anchor="w", fg_color="transparent", text_color="#32d74b", hover_color="#3a3a3c", font=("SF Pro Text", 12), command=self.export_chat).pack(fill="x", pady=1)
        ctk.CTkButton(bottom_menu, text="📂  Importieren", anchor="w", fg_color="transparent", text_color="#0a84ff", hover_color="#3a3a3c", font=("SF Pro Text", 12), command=self.import_chat).pack(fill="x", pady=1)

        self.refresh_sidebar_history()

        # Hauptcontainer (Glas-Optik Frame)
        self.main_container = ctk.CTkFrame(self, fg_color="#2c2c2e" if not self.glass_mode.get() else "#1e1e1e", corner_radius=12)
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self.main_container, fg_color="transparent" if self.glass_mode.get() else None)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.tab_main = self.tabview.add("Chat")
        self.tab_admin = self.tabview.add("Admin-Panel 🛠️")
        self.tab_settings = self.tabview.add("Einstellungen ⚙️")
        self.tab_legal = self.tabview.add("Impressum ⚖️")

        self.setup_main_tab()
        self.setup_admin_tab()
        self.setup_settings_tab()
        self.setup_legal_tab()

    def show_soon(self, feature):
        messagebox.showinfo("macOS Feature", f"'{feature}' befindet sich in Entwicklung für macOS.")

    def refresh_sidebar_history(self):
        for widget in self.scroll_history.winfo_children():
            widget.destroy()

        for chat_id, first_msg, _, is_pinned in get_all_chat_sessions():
            title = first_msg if len(first_msg) <= 22 else first_msg[:20] + "..."
            icon = "📌 " if is_pinned == 1 else "💬 "
            btn_bg = "#3a3a3c" if chat_id == self.current_chat_id else "transparent"

            btn = ctk.CTkButton(
                self.scroll_history, text=f"{icon}{title}", anchor="w", fg_color=btn_bg,
                text_color="#0a84ff" if is_pinned == 1 else "#ffffff", hover_color="#3a3a3c",
                font=("SF Pro Text", 12), command=lambda c=chat_id: self.load_selected_chat(c)
            )
            btn.pack(fill="x", pady=2)
            btn.bind("<Button-2>", lambda e, c=chat_id, p=is_pinned: self.show_context_menu(e, c, p))
            btn.bind("<Button-3>", lambda e, c=chat_id, p=is_pinned: self.show_context_menu(e, c, p))

    def show_context_menu(self, event, chat_id, is_pinned):
        menu = tk.Menu(self, tearoff=0, bg="#2c2c2e", fg="#ffffff", activebackground="#0a84ff", activeforeground="#ffffff")
        menu.add_command(label="📌 Loslösen" if is_pinned == 1 else "📌 Anheften", command=lambda: [toggle_pin_chat(chat_id), self.refresh_sidebar_history()])
        menu.add_separator()
        menu.add_command(label="🗑️ Löschen", command=lambda: [delete_chat_session(chat_id), self.start_new_chat() if self.current_chat_id == chat_id else self.refresh_sidebar_history()])
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def load_selected_chat(self, chat_id):
        self.current_chat_id = chat_id
        self.txt_output.delete("1.0", tk.END)
        conn = sqlite3.connect("ki_gedaechtnis.db")
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM chats WHERE chat_id = ? ORDER BY id ASC", (chat_id,))
        for role, content in cursor.fetchall():
            prefix = "👤 Du:\n" if role == "user" else "🍏 Bany AI:\n"
            self.txt_output.insert(tk.END, f"\n{prefix}{content}\n\n" + "—"*45 + "\n")
        conn.close()
        self.txt_output.see(tk.END)
        self.refresh_sidebar_history()

    # --- 10 LIVE WALLPAPERS ENGINE ---
    def animate_live_background(self):
        if self.animated_mode.get():
            self.anim_step += 0.03
            w, h = self.winfo_width(), self.winfo_height()
            if w > 10 and h > 10:
                self.bg_canvas.delete("live_wp")
                
                # 1. macOS Sequoia Aurora
                if self.current_wallpaper == "macOS Sequoia Aurora":
                    for i in range(5):
                        x = (w * 0.5) + math.sin(self.anim_step * 0.5 + i) * (w * 0.4)
                        y = (h * 0.5) + math.cos(self.anim_step * 0.3 + i) * (h * 0.3)
                        self.bg_canvas.create_oval(x-200, y-200, x+200, y+200, fill="#0a84ff" if i%2==0 else "#bf5af2", outline="", stipple="gray25", tags="live_wp")
                
                # 2. Cyberpunk Neon Rain
                elif self.current_wallpaper == "Cyberpunk Neon Rain":
                    for i in range(15):
                        x = (i * 80 + int(self.anim_step * 20)) % w
                        y = (i * 50 + int(self.anim_step * 50)) % h
                        self.bg_canvas.create_line(x, y, x, y+30, fill="#ff2d55", width=2, tags="live_wp")

                # 3. Deep Ocean Blue
                elif self.current_wallpaper == "Deep Ocean Blue":
                    for i in range(4):
                        y_pos = h * (0.2 * i) + math.sin(self.anim_step + i) * 30
                        self.bg_canvas.create_rectangle(0, y_pos, w, y_pos+150, fill="#003b46" if i%2==0 else "#07575b", outline="", stipple="gray50", tags="live_wp")

                # 4. Sunset Orange Glow
                elif self.current_wallpaper == "Sunset Orange Glow":
                    x = w * 0.5 + math.sin(self.anim_step * 0.4) * (w * 0.3)
                    y = h * 0.3 + math.cos(self.anim_step * 0.2) * 50
                    self.bg_canvas.create_oval(x-300, y-300, x+300, y+300, fill="#ff9f0a", outline="", stipple="gray25", tags="live_wp")

                # 5. Matrix Green Stream
                elif self.current_wallpaper == "Matrix Green Stream":
                    for i in range(12):
                        x = (i * 90)
                        y = (int(self.anim_step * 40) + i * 70) % h
                        self.bg_canvas.create_text(x, y, text="01101001", fill="#32d74b", font=("Courier", 12), tags="live_wp")

                # 6. Minimalist Gray Mist
                elif self.current_wallpaper == "Minimalist Gray Mist":
                    x = w * 0.5 + math.cos(self.anim_step * 0.3) * (w * 0.2)
                    self.bg_canvas.create_oval(x-250, 100, x+250, 400, fill="#48484a", outline="", stipple="gray50", tags="live_wp")

                # 7. Midnight Purple Void
                elif self.current_wallpaper == "Midnight Purple Void":
                    x = w * 0.5 + math.sin(self.anim_step * 0.5) * (w * 0.4)
                    y = h * 0.5 + math.sin(self.anim_step * 0.3) * (h * 0.4)
                    self.bg_canvas.create_oval(x-180, y-180, x+180, y+180, fill="#5856d6", outline="", stipple="gray25", tags="live_wp")

                # 8. Golden Desert Mirage
                elif self.current_wallpaper == "Golden Desert Mirage":
                    y = h * 0.7 + math.sin(self.anim_step * 0.4) * 20
                    self.bg_canvas.create_rectangle(0, y, w, h, fill="#d4af37", outline="", stipple="gray50", tags="live_wp")

                # 9. Frosty Arctic Wave
                elif self.current_wallpaper == "Frosty Arctic Wave":
                    for i in range(3):
                        x = w * 0.5 + math.cos(self.anim_step + i) * 200
                        self.bg_canvas.create_oval(x-150, i*150, x+150, i*150+200, fill="#64d2ff", outline="", stipple="gray25", tags="live_wp")

                # 10. Dynamic Citrus Lemon
                elif self.current_wallpaper == "Dynamic Citrus Lemon":
                    x = w * 0.5 + math.sin(self.anim_step * 0.6) * (w * 0.3)
                    y = h * 0.5 + math.cos(self.anim_step * 0.6) * (h * 0.3)
                    self.bg_canvas.create_oval(x-200, y-200, x+200, y+200, fill="#ffd60a", outline="", stipple="gray25", tags="live_wp")

        self.after(50, self.animate_live_background)

    def setup_main_tab(self):
        self.tab_main.grid_columnconfigure(0, weight=1)
        self.tab_main.grid_rowconfigure(1, weight=1)

        status_frame = ctk.CTkFrame(self.tab_main, fg_color="transparent")
bereit = status_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 0))
        status_frame.grid_columnconfigure(1, weight=1)

        self.lbl_status = ctk.CTkLabel(status_frame, text="🍏 Bereit", font=("SF Pro Text", 12), text_color="#888888")
        self.lbl_status.grid(row=0, column=0, sticky="w")

        self.txt_output = ctk.CTkTextbox(self.tab_main, font=("SF Pro Text", self.current_font_size), wrap="word", fg_color="transparent" if self.glass_mode.get() else None)
        self.txt_output.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        chat_bottom = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        chat_bottom.grid(row=2, column=0, sticky="ew", padx=5, pady=10)
        chat_bottom.grid_columnconfigure(0, weight=1)

        input_frame = ctk.CTkFrame(chat_bottom, fg_color="transparent")
        input_frame.grid(row=0, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.entry_query = ctk.CTkEntry(input_frame, placeholder_text="Nachricht an Bany AI...", height=40, font=("SF Pro Text", 14), fg_color="#3a3a3c" if self.glass_mode.get() else None)
        self.entry_query.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry_query.bind("<Return>", lambda e: self.start_search_thread())

        self.btn_search = ctk.CTkButton(input_frame, text="Senden", height=40, width=90, font=("SF Pro Text", 13, "bold"), fg_color="#0a84ff", text_color="white", command=self.start_search_thread)
        self.btn_search.grid(row=0, column=1)

        tts_frame = ctk.CTkFrame(chat_bottom, fg_color="transparent")
        tts_frame.grid(row=1, column=0, sticky="e", pady=(5, 0))
        self.switch_tts = ctk.CTkSwitch(tts_frame, text="Sprachausgabe (TTS)", variable=self.tts_enabled, command=self.save_settings, font=("SF Pro Text", 11))
        self.switch_tts.pack(side="right")

    def start_new_chat(self):
        self.current_chat_id = str(uuid.uuid4())
        self.txt_output.delete("1.0", tk.END)
        self.refresh_sidebar_history()

    def export_chat(self):
        conn = sqlite3.connect("ki_gedaechtnis.db")
        cursor = conn.cursor()
        cursor.execute("SELECT role, content, timestamp FROM chats WHERE chat_id = ? ORDER BY id ASC", (self.current_chat_id,))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            messagebox.showwarning("Export", "Chat ist leer!")
            return
        folder = filedialog.askdirectory(initialdir=os.path.expanduser("~/Desktop"))
        if folder:
            path = os.path.join(folder, f"bany_mac_chat_{self.current_chat_id[:8]}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump([{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows], f, indent=4)
            messagebox.showinfo("Export", f"Gespeichert unter:\n{path}")

    def import_chat(self):
        path = filedialog.askopenfilename(initialdir=os.path.expanduser("~/Desktop"), filetypes=[("JSON", "*.json")])
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.current_chat_id = str(uuid.uuid4())
                self.txt_output.delete("1.0", tk.END)
                for item in data:
                    save_chat_message(self.current_chat_id, item.get("role"), item.get("content"))
                self.load_selected_chat(self.current_chat_id)
            except Exception as e:
                messagebox.showerror("Fehler", str(e))

    def search_chats_dialog(self):
        q = simpledialog.askstring("Suche", "Begriff in Chats suchen:")
        if q:
            conn = sqlite3.connect("ki_gedaechtnis.db")
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM chats WHERE content LIKE ? LIMIT 5", (f"%{q}%",))
            res = cursor.fetchall()
            conn.close()
            messagebox.showinfo("Ergebnisse", "\n\n".join([f"- {r[0][:100]}..." for r in res]) if res else "Keine Treffer.")

    def start_search_thread(self):
        query = self.entry_query.get().strip()
        if not query:
            return
        self.btn_search.configure(state="disabled")
        self.lbl_status.configure(text="🍏 Generiere Antwort...")
        threading.Thread(target=self.process_query, args=(query,), daemon=True).start()

    def process_query(self, query):
        try:
            fb = get_firebase_answer(query)
            if fb:
                answer = fb + "\n\n✨ (Aus dem globalen Team-Gedächtnis)"
            else:
                history = load_chat_history(self.current_chat_id)
                search_res = ""
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=3):
                        search_res += f"- {r.get('body', '')}\n"
                sys_inst = load_system_prompt()
                if search_res:
                    sys_inst += f"\n\nWeb-Suchergebnisse:\n{search_res}"
                history.append(types.Content(role="user", parts=[types.Part.from_text(text=query)]))
                response = self.client.models.generate_content(model="gemini-2.5-flash", contents=history, config=types.GenerateContentConfig(system_instruction=sys_inst))
                answer = response.text

            save_chat_message(self.current_chat_id, "user", query)
            save_chat_message(self.current_chat_id, "model", answer)

            conn = sqlite3.connect("ki_gedaechtnis.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO anfragen (frage, antwort, status) VALUES (?, ?, ?)", (query, answer, "Gelernt" if fb else "Ungeprüft"))
            conn.commit()
            conn.close()

            self.after(0, lambda: self.update_ui(query, answer))
            if self.tts_enabled.get():
                threading.Thread(target=lambda: pyttsx3.init().say(answer) or pyttsx3.init().runAndWait(), daemon=True).start()
        except Exception as e:
            self.after(0, lambda: self.update_ui(query, f"Fehler: {e}", True))

    def update_ui(self, query, answer, is_error=False):
        self.txt_output.insert(tk.END, f"\n👤 Du:\n{query}\n\n🍏 Bany AI:\n{answer}\n\n" + "—"*45 + "\n")
        self.lbl_status.configure(text="🍏 Bereit")
        self.txt_output.see(tk.END)
        self.btn_search.configure(state="normal")
        if not is_error:
            self.entry_query.delete(0, tk.END)
        self.refresh_sidebar_history()

    def setup_admin_tab(self):
        self.tab_admin.grid_columnconfigure(0, weight=1)
        self.tab_admin.grid_rowconfigure(0, weight=1)
        self.frame_login = ctk.CTkFrame(self.tab_admin, fg_color="transparent")
        self.frame_login.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        ctk.CTkLabel(self.frame_login, text="Admin-Login (macOS)", font=("SF Pro Display", 18, "bold")).pack(pady=(40, 20))
        self.entry_user = ctk.CTkEntry(self.frame_login, placeholder_text="Benutzername", width=250, height=35)
        self.entry_user.pack(pady=10)
        self.entry_pass = ctk.CTkEntry(self.frame_login, placeholder_text="Passwort", show="*", width=250, height=35)
        self.entry_pass.pack(pady=10)
        ctk.CTkButton(self.frame_login, text="Anmelden", command=self.check_login, width=250, fg_color="#0a84ff").pack(pady=20)

        self.frame_dashboard = ctk.CTkFrame(self.tab_admin, fg_color="transparent")
        self.frame_dashboard.grid_columnconfigure(0, weight=1)
        self.frame_dashboard.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.frame_dashboard, text="Gedächtnis-Verwaltung", font=("SF Pro Display", 16, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.scroll_admin = ctk.CTkScrollableFrame(self.frame_dashboard, fg_color="transparent")
        self.scroll_admin.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.scroll_admin.grid_columnconfigure(0, weight=1)

    def check_login(self):
        if self.entry_user.get() == "Pralle" and self.entry_pass.get() == "4459":
            self.is_admin_logged_in = True
            self.frame_login.grid_forget()
            self.frame_dashboard.grid(row=0, column=0, sticky="nsew")
            self.load_admin_dashboard()
        else:
            messagebox.showerror("Fehler", "Falsche Zugangsdaten!")

    def load_admin_dashboard(self):
        for w in self.scroll_admin.winfo_children():
            w.destroy()
        conn = sqlite3.connect("ki_gedaechtnis.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, frage, antwort, status FROM anfragen ORDER BY id DESC")
        for req_id, frage, antwort, status in cursor.fetchall():
            card = ctk.CTkFrame(self.scroll_admin, fg_color="#2d2d2d")
            card.pack(fill="x", pady=5, padx=5)
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text=f"ID #{req_id} | Status: {status}", font=("SF Pro Text", 11, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
            ctk.CTkLabel(card, text=f"F: {frage}\nA: {antwort}", font=("SF Pro Text", 11), justify="left", wraplength=650).grid(row=1, column=0, sticky="w", padx=10, pady=5)
            if status == "Ungeprüft":
                ctk.CTkButton(card, text="✅ Korrekt", fg_color="#32d74b", width=80, command=lambda r=req_id, f=frage, a=antwort: [save_firebase_answer(f, a), self.set_status(r, "Korrigiert")]).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        conn.close()

    def set_status(self, req_id, status):
        conn = sqlite3.connect("ki_gedaechtnis.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE anfragen SET status = ? WHERE id = ?", (status, req_id))
        conn.commit()
        conn.close()
        self.load_admin_dashboard()

    def setup_settings_tab(self):
        frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="🎨 macOS Einstellungen & Glass Mode", font=("SF Pro Display", 16, "bold")).pack(anchor="w", pady=(0, 15))

        self.switch_glass = ctk.CTkSwitch(frame, text="Glass Mode aktivieren (Transparenter Mac-Look)", variable=self.glass_mode, command=self.toggle_glass_mode)
        self.switch_glass.pack(anchor="w", pady=10)

        self.switch_anim = ctk.CTkSwitch(frame, text="Live Wallpapers & Animationen aktiv", variable=self.animated_mode, command=self.save_settings)
        self.switch_anim.pack(anchor="w", pady=10)

        ctk.CTkLabel(frame, text="Live Hintergrund wählen (10 Optionen):", font=("SF Pro Text", 12, "bold")).pack(anchor="w", pady=(15, 5))
        self.combo_wp = ctk.CTkOptionMenu(frame, values=LIVE_WALLPAPERS, command=self.change_wallpaper)
        self.combo_wp.set(self.current_wallpaper)
        self.combo_wp.pack(anchor="w", pady=5)

        ctk.CTkLabel(frame, text="Theme Preset:", font=("SF Pro Text", 12, "bold")).pack(anchor="w", pady=(15, 5))
        self.combo_theme = ctk.CTkOptionMenu(frame, values=list(THEMES.keys()), command=self.change_theme_event)
        self.combo_theme.set(self.current_theme_name)
        self.combo_theme.pack(anchor="w", pady=5)

    def toggle_glass_mode(self):
        is_glass = self.glass_mode.get()
        new_bg = "#1e1e1e" if is_glass else "#2c2c2e"
        sidebar_bg = "#1a1a1a" if is_glass else "#262626"
        self.sidebar_frame.configure(fg_color=sidebar_bg)
        self.main_container.configure(fg_color=new_bg)
        self.save_settings()

    def change_wallpaper(self, choice):
        self.current_wallpaper = choice
        self.save_settings()

    def change_theme_event(self, choice):
        self.current_theme_name = choice
        self.current_theme = THEMES[choice]
        self.configure(fg_color=self.current_theme["bg"])
        self.save_settings()

    def setup_legal_tab(self):
        txt = ctk.CTkTextbox(self.tab_legal, font=("SF Pro Text", 12), wrap="word", fg_color="transparent")
        txt.pack(fill="both", expand=True, padx=15, pady=15)
        txt.insert("1.0", "Bany AI macOS Edition\nDesigned with Glassmorphism & 10 Live Wallpapers.\n© 2026 Aether Software.")
        txt.configure(state="disabled")

if __name__ == "__main__":
    app = AetherOSAssistant()
    app.mainloop()