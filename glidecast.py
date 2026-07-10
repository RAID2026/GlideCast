import os
import sys
import socket
import ctypes
import subprocess
import threading
import time
import urllib.request
import zipfile
import shutil
import tkinter as tk
import tkinter.messagebox as messagebox
import customtkinter as ctk

# ----------------- SINGLE INSTANCE LOCK -----------------
# Bind a local socket to prevent multiple instances from running
# and conflicting with ADB connections
try:
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Port 28430 is selected arbitrarily
    lock_socket.bind(('127.0.0.1', 28430))
except socket.error:
    # Another instance is already running
    root = tk.Tk()
    root.withdraw() # Hide main window
    messagebox.showerror(
        "GlideCast", 
        "Another instance of GlideCast is already running.\n"
        "Please close the active instance before launching a new one."
    )
    sys.exit(0)

# ----------------- APP CONFIGURATION -----------------
VERSION = "v1.0.0"
SCRCPY_VERSION = "2.4"
SCRCPY_URL = f"https://github.com/Genymobile/scrcpy/releases/download/v{SCRCPY_VERSION}/scrcpy-win64-v{SCRCPY_VERSION}.zip"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Store downloaded binaries in the user's Local AppData directory 
# to prevent PermissionErrors if the app is installed in C:\Program Files
LOCAL_DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "GlideCast")
BIN_DIR = os.path.join(LOCAL_DATA_DIR, "bin")
SCRCPY_DIR = os.path.join(BIN_DIR, f"scrcpy-win64-v{SCRCPY_VERSION}")
ADB_PATH = os.path.join(SCRCPY_DIR, "adb.exe")
SCRCPY_PATH = os.path.join(SCRCPY_DIR, "scrcpy.exe")
ICON_PATH = resource_path("glidecast.ico")

class GlideCastApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("GlideCast - Android Screen Mirroring")
        self.geometry("780x640")
        self.minsize(720, 600)
        
        # Keep lock socket alive inside the app instance
        self.lock_socket = lock_socket
        
        # Theme configuration
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Load window icon if it exists
        if os.path.exists(ICON_PATH):
            try:
                self.iconbitmap(ICON_PATH)
            except Exception:
                pass
        
        # State variables
        self.devices = []
        self.mirror_process = None
        self.demo_window = None
        self.downloading = False
        self.scanning = False
        
        # UI Setup
        self.setup_ui()
        
        # Start initialization check in background
        self.after(500, self.check_dependencies)

    def setup_ui(self):
        # Configure grid layout (2 columns, 1 row)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # Left Panel (Settings & Control)
        self.left_panel = ctk.CTkFrame(self, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(9, weight=1) # Spacer

        # App Title / Brand
        self.title_label = ctk.CTkLabel(
            self.left_panel, 
            text="GLIDECAST", 
            font=ctk.CTkFont(size=24, weight="bold", family="Segoe UI"),
            text_color="#06b6d4" # Smooth cyan accent
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(30, 5))
        
        self.version_label = ctk.CTkLabel(
            self.left_panel,
            text=f"Version {VERSION} | Engine v{SCRCPY_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.version_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Device Selection
        self.device_label = ctk.CTkLabel(self.left_panel, text="Android Device", font=ctk.CTkFont(weight="bold"))
        self.device_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.device_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.device_frame.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.device_frame.grid_columnconfigure(0, weight=1)
        
        self.device_dropdown = ctk.CTkOptionMenu(
            self.device_frame, 
            values=["No devices detected"],
            fg_color="#0891b2", # Cyan colors
            button_color="#0891b2",
            button_hover_color="#06b6d4"
        )
        self.device_dropdown.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        self.scan_btn = ctk.CTkButton(
            self.device_frame, 
            text="Scan", 
            width=60, 
            command=self.start_device_scan,
            fg_color="#1f2937",
            hover_color="#374151"
        )
        self.scan_btn.grid(row=0, column=1, sticky="e")

        # Mirroring Settings
        self.settings_label = ctk.CTkLabel(self.left_panel, text="Mirror Settings", font=ctk.CTkFont(weight="bold"))
        self.settings_label.grid(row=4, column=0, padx=20, pady=(10, 5), sticky="w")

        # Config: Resolution
        self.res_label = ctk.CTkLabel(self.left_panel, text="Max Resolution limit:", font=ctk.CTkFont(size=12))
        self.res_label.grid(row=5, column=0, padx=25, pady=(5, 2), sticky="w")
        self.res_dropdown = ctk.CTkOptionMenu(
            self.left_panel, 
            values=["Auto (Native)", "1920 (1080p)", "1280 (720p)", "1024 (Normal)", "800 (Fast)"],
            fg_color="#1f2937",
            button_color="#374151"
        )
        self.res_dropdown.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.res_dropdown.set("Auto (Native)") # Set to Native default for best view

        # Config: Bitrate
        self.bit_label = ctk.CTkLabel(self.left_panel, text="Video Bitrate:", font=ctk.CTkFont(size=12))
        self.bit_label.grid(row=7, column=0, padx=25, pady=(5, 2), sticky="w")
        self.bit_dropdown = ctk.CTkOptionMenu(
            self.left_panel, 
            values=["2 Mbps (Fast)", "4 Mbps (Balanced)", "8 Mbps (High Quality)", "16 Mbps (Ultra)"],
            fg_color="#1f2937",
            button_color="#374151"
        )
        self.bit_dropdown.grid(row=8, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.bit_dropdown.set("8 Mbps (High Quality)")

        # Spacer in row 9

        # Control Switch Panel (Audio, Screen Off, Stay on Top)
        self.switch_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.switch_frame.grid(row=10, column=0, padx=20, pady=15, sticky="ew")
        self.switch_frame.grid_columnconfigure(0, weight=1)

        self.screen_off_switch = ctk.CTkSwitch(self.switch_frame, text="Turn off phone screen", progress_color="#0891b2")
        self.screen_off_switch.grid(row=0, column=0, sticky="w", pady=5)
        
        self.audio_switch = ctk.CTkSwitch(self.switch_frame, text="Forward Audio", progress_color="#0891b2")
        self.audio_switch.grid(row=1, column=0, sticky="w", pady=5)
        self.audio_switch.select() # Default ON

        self.stay_on_top_switch = ctk.CTkSwitch(self.switch_frame, text="Keep window on top", progress_color="#0891b2")
        self.stay_on_top_switch.grid(row=2, column=0, sticky="w", pady=5)

        self.control_switch = ctk.CTkSwitch(self.switch_frame, text="Enable PC Control (Mouse/KB)", progress_color="#0891b2")
        self.control_switch.grid(row=3, column=0, sticky="w", pady=5)
        self.control_switch.select() # Default ON

        # Launch Button
        self.launch_btn = ctk.CTkButton(
            self.left_panel, 
            text="START MIRRORING", 
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#0891b2",
            hover_color="#06b6d4",
            command=self.toggle_mirroring,
            state="disabled" # Disabled until dependencies check out
        )
        self.launch_btn.grid(row=11, column=0, padx=20, pady=(10, 25), sticky="ew")

        # Right Panel (Tabbed: Guide vs Licenses)
        self.right_panel = ctk.CTkTabview(
            self, 
            segmented_button_selected_color="#0891b2",
            segmented_button_selected_hover_color="#06b6d4",
            fg_color="#0f172a"
        )
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        # Tabs setup
        self.guide_tab = self.right_panel.add("How to Connect")
        self.license_tab = self.right_panel.add("Licenses & About")
        
        self.setup_guide_tab()
        self.setup_license_tab()

    def setup_guide_tab(self):
        self.guide_tab.grid_columnconfigure(0, weight=1)
        self.guide_tab.grid_rowconfigure(2, weight=1)

        # Title
        self.guide_title = ctk.CTkLabel(
            self.guide_tab, 
            text="Connection Assistant", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.guide_title.grid(row=0, column=0, padx=10, pady=(15, 10), sticky="w")

        # Guide Steps
        guide_text = (
            "1. Connect your phone to your PC via a USB cable.\n\n"
            "2. Make sure USB Debugging is enabled on your phone:\n"
            "   • Go to Settings > About Phone\n"
            "   • Tap 'Build number' 7 times to enable Developer options\n"
            "   • Go back to Settings > System > Developer options\n"
            "   • Toggle 'USB Debugging' ON\n\n"
            "3. Look at your phone! A popup will ask you to authorize this PC.\n"
            "   • Check 'Always allow from this computer' and tap 'Allow'.\n\n"
            "4. Select your device from the dropdown on the left and click\n"
            "   'START MIRRORING'."
        )
        self.guide_box = ctk.CTkTextbox(
            self.guide_tab, 
            height=190, 
            fg_color="#1e293b", 
            border_color="#334155", 
            border_width=1,
            font=ctk.CTkFont(size=12)
        )
        self.guide_box.grid(row=1, column=0, padx=10, pady=(0, 15), sticky="ew")
        self.guide_box.insert("1.0", guide_text)
        self.guide_box.configure(state="disabled")

        # Log & Status Terminal
        self.terminal_label = ctk.CTkLabel(
            self.guide_tab, 
            text="Status Logs", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.terminal_label.grid(row=2, column=0, padx=10, pady=(10, 2), sticky="w")

        self.terminal = ctk.CTkTextbox(
            self.guide_tab, 
            fg_color="#020617", 
            border_color="#1e293b", 
            border_width=1,
            text_color="#22d3ee", # Cyan logs
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.terminal.grid(row=3, column=0, padx=10, pady=(0, 15), sticky="nsew")
        self.log("[System] Initializing GlideCast...")

    def setup_license_tab(self):
        self.license_tab.grid_columnconfigure(0, weight=1)
        self.license_tab.grid_rowconfigure(1, weight=1)

        # Title
        license_title = ctk.CTkLabel(
            self.license_tab, 
            text="Open Source Attribution", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        license_title.grid(row=0, column=0, padx=10, pady=(15, 10), sticky="w")

        license_text = (
            "GlideCast is a frontend utility that distributes and bundles open source components:\n\n"
            "• scrcpy (Engine)\n"
            "  Version: 2.4\n"
            "  License: Apache License 2.0\n"
            "  Source: https://github.com/Genymobile/scrcpy\n\n"
            "• Android Debug Bridge (ADB)\n"
            "  License: Apache License 2.0 / Android SDK License\n"
            "  Source: https://developer.android.com/studio/releases/platform-tools\n\n"
            "--------------------------------------------------\n"
            "Apache License 2.0 Notice:\n"
            "Licensed under the Apache License, Version 2.0 (the \"License\"); "
            "you may not use this file except in compliance with the License. "
            "You may obtain a copy of the License at:\n"
            "http://www.apache.org/licenses/LICENSE-2.0\n\n"
            "Unless required by applicable law or agreed to in writing, software "
            "distributed under the License is distributed on an \"AS IS\" BASIS, "
            "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied."
        )
        self.license_box = ctk.CTkTextbox(
            self.license_tab, 
            fg_color="#1e293b", 
            border_color="#334155", 
            border_width=1,
            font=ctk.CTkFont(size=12)
        )
        self.license_box.grid(row=1, column=0, padx=10, pady=(0, 15), sticky="nsew")
        self.license_box.insert("1.0", license_text)
        self.license_box.configure(state="disabled")

    def log(self, message):
        self.terminal.configure(state="normal")
        self.terminal.insert("end", f"{message}\n")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def check_dependencies(self):
        self.log("[System] Checking ADB and scrcpy engines...")
        
        # Check if already installed in Local AppData
        if os.path.exists(ADB_PATH) and os.path.exists(SCRCPY_PATH):
            self.log("[System] Dependencies found! Engine is ready.")
            self.launch_btn.configure(state="normal")
            self.start_device_scan()
            return
            
        # If not, check if we have bundled binaries inside the app package
        bundled_dir = resource_path(os.path.join("bin", f"scrcpy-win64-v{SCRCPY_VERSION}"))
        if os.path.exists(bundled_dir):
            self.log("[System] Initializing bundled engine binaries...")
            try:
                os.makedirs(BIN_DIR, exist_ok=True)
                # Copy from bundle to Local AppData
                shutil.copytree(bundled_dir, SCRCPY_DIR, dirs_exist_ok=True)
                self.log("[System] Engine initialized successfully!")
                self.launch_btn.configure(state="normal")
                self.start_device_scan()
            except Exception as e:
                self.log(f"[Error] Failed to initialize bundled engine: {str(e)}")
                messagebox.showerror(
                    "Initialization Error",
                    f"Failed to copy engine binaries to AppData:\n\n{str(e)}"
                )
            return

        # Fallback to downloading from GitHub (for raw script developer runs)
        self.log("[System] No local or bundled engine found. Starting download...")
        self.prompt_download()

    def prompt_download(self):
        self.download_window = ctk.CTkToplevel(self)
        self.download_window.title("Downloading Dependencies")
        self.download_window.geometry("400x200")
        self.download_window.resizable(False, False)
        self.download_window.transient(self) # Keep on top of main window
        self.download_window.grab_set()      # Modal window

        # Handle modal window exit
        self.download_window.protocol("WM_DELETE_WINDOW", self.on_download_cancel)

        label = ctk.CTkLabel(
            self.download_window, 
            text="Downloading scrcpy & ADB tools\n(Approx. 6MB)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label.pack(pady=20)

        self.progress_bar = ctk.CTkProgressBar(self.download_window, width=300)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self.download_window, text="Preparing download...")
        self.status_label.pack(pady=5)

        # Run download in a background thread
        self.download_thread = threading.Thread(target=self.download_engine_thread, daemon=True)
        self.download_thread.start()

    def on_download_cancel(self):
        if self.downloading:
            if messagebox.askyesno("Cancel Download", "Are you sure you want to cancel the download? GlideCast cannot run without these tools."):
                self.download_window.destroy()
                self.destroy()
        else:
            self.download_window.destroy()

    def download_engine_thread(self):
        try:
            self.downloading = True
            
            # Make sure bin folder exists
            os.makedirs(BIN_DIR, exist_ok=True)
            zip_path = os.path.join(BIN_DIR, "scrcpy_temp.zip")

            self.log(f"[Downloader] Downloading engine from: {SCRCPY_URL}")
            
            def report_progress(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(1.0, (block_num * block_size) / total_size)
                    self.progress_bar.set(percent)
                    self.status_label.configure(text=f"Downloaded {int(percent * 100)}%")
            
            # Download file
            urllib.request.urlretrieve(SCRCPY_URL, zip_path, reporthook=report_progress)
            
            self.status_label.configure(text="Extracting files...")
            self.log("[Downloader] Extracting zip file...")
            
            # Extract zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(BIN_DIR)
                
            # Clean up zip
            os.remove(zip_path)
            
            self.log("[Downloader] Installation completed successfully!")
            self.downloading = False
            
            # Close dialog and enable UI
            self.download_window.after(500, self.download_window.destroy)
            self.after(600, lambda: self.launch_btn.configure(state="normal"))
            self.after(700, self.start_device_scan)
            
        except Exception as e:
            self.downloading = False
            self.log(f"[Error] Failed to install dependencies: {str(e)}")
            self.log("[Error] Make sure you are connected to the internet and try again.")
            
            # Show friendly alert box on main thread
            self.after(0, lambda: messagebox.showerror(
                "Connection Error", 
                "Failed to download the screen mirroring engine.\n\n"
                "Please verify your internet connection and restart GlideCast to try again."
            ))
            
            # Close download window and keep start disabled
            self.download_window.after(100, self.download_window.destroy)

    def start_device_scan(self):
        if self.scanning:
            return
        
        self.scanning = True
        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.log("[ADB] Scanning for connected Android devices...")
        
        threading.Thread(target=self.scan_devices_thread, daemon=True).start()

    def scan_devices_thread(self):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.run(
                [ADB_PATH, "devices"], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            lines = process.stdout.strip().split("\n")
            devices = []
            
            for line in lines[1:]:
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1]
                    devices.append((serial, state))
            
            self.devices = devices
            self.after(0, self.update_device_ui)
            
        except Exception as e:
            self.log(f"[Error] Failed to scan devices: {str(e)}")
            self.after(0, lambda: self.scan_btn.configure(state="normal", text="Scan"))
            self.scanning = False

    def update_device_ui(self):
        self.scanning = False
        self.scan_btn.configure(state="normal", text="Scan")
        
        if not self.devices:
            self.device_dropdown.configure(values=["No devices detected", "Demo Simulation (virtual)"])
            self.device_dropdown.set("No devices detected")
            self.log("[ADB] No active devices found. Make sure USB Debugging is ON.")
        else:
            dropdown_values = []
            for serial, state in self.devices:
                dropdown_values.append(f"{serial} ({state})")
            dropdown_values.append("Demo Simulation (virtual)")
            self.device_dropdown.configure(values=dropdown_values)
            self.device_dropdown.set(dropdown_values[0])
            self.log(f"[ADB] Found {len(self.devices)} device(s) connected.")

    def get_selected_device_serial(self):
        selected = self.device_dropdown.get()
        if selected == "Demo Simulation (virtual)":
            return "Demo_Simulation"
        if selected == "No devices detected" or not self.devices:
            return None
        return selected.split(" ")[0]

    def toggle_mirroring(self):
        if self.mirror_process is not None or (hasattr(self, "demo_window") and self.demo_window is not None):
            self.stop_mirroring()
        else:
            self.start_mirroring()

    def start_mirroring(self):
        serial = self.get_selected_device_serial()
        if not serial:
            self.log("[Error] Please select a valid device and scan again.")
            return

        if serial == "Demo_Simulation":
            self.run_demo_simulation()
            return

        # Build scrcpy arguments
        args = [SCRCPY_PATH, "-s", serial]

        # Resolution dropdown parsing
        res_sel = self.res_dropdown.get()
        if "1920" in res_sel:
            args.extend(["-m", "1920"])
        elif "1280" in res_sel:
            args.extend(["-m", "1280"])
        elif "1024" in res_sel:
            args.extend(["-m", "1024"])
        elif "800" in res_sel:
            args.extend(["-m", "800"])

        # Bitrate dropdown parsing
        bit_sel = self.bit_dropdown.get()
        if "2 Mbps" in bit_sel:
            args.extend(["-b", "2M"])
        elif "4 Mbps" in bit_sel:
            args.extend(["-b", "4M"])
        elif "8 Mbps" in bit_sel:
            args.extend(["-b", "8M"])
        elif "16 Mbps" in bit_sel:
            args.extend(["-b", "16M"])

        # Switches
        if self.screen_off_switch.get():
            args.append("--turn-screen-off")
            
        if not self.audio_switch.get():
            args.append("--no-audio")

        if self.stay_on_top_switch.get():
            args.append("--always-on-top")

        if not self.control_switch.get():
            args.append("--no-control")

        # Custom window title
        args.append(f"--window-title=GlideCast: {serial}")

        self.log(f"[Mirror] Starting screen mirror for: {serial}...")

        # Launch mirroring process
        try:
            self.mirror_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Disable buttons while active
            self.launch_btn.configure(text="STOP MIRRORING", fg_color="#ef4444", hover_color="#dc2626")
            self.scan_btn.configure(state="disabled")
            self.device_dropdown.configure(state="disabled")
            
            # Start a thread to watch the process completion
            threading.Thread(target=self.monitor_process_thread, daemon=True).start()
            
            # Start a thread to apply the custom icon to the scrcpy window
            window_title = f"GlideCast: {serial}"
            threading.Thread(target=self.apply_mirror_window_icon_thread, args=(window_title,), daemon=True).start()
            
        except Exception as e:
            self.log(f"[Error] Failed to start mirroring: {str(e)}")
            self.mirror_process = None

    def apply_mirror_window_icon_thread(self, window_title):
        # Wait for the scrcpy window to appear (check every 100ms for up to 5s)
        icon_path = ICON_PATH
        if not os.path.exists(icon_path):
            return
            
        for _ in range(50):
            time.sleep(0.1)
            hwnd = ctypes.windll.user32.FindWindowW(None, window_title)
            if hwnd:
                try:
                    # Load the .ico file
                    # IMAGE_ICON = 1, LR_LOADFROMFILE = 0x00000010, LR_DEFAULTSIZE = 0x00000040
                    hicon = ctypes.windll.user32.LoadImageW(
                        None,
                        icon_path,
                        1, # IMAGE_ICON
                        0, 0,
                        0x00000010 | 0x00000040
                    )
                    if hicon:
                        # WM_SETICON = 0x0080
                        # ICON_SMALL = 0, ICON_BIG = 1
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)
                        break
                except Exception as e:
                    print(f"Error setting window icon: {e}")
                    break

    def monitor_process_thread(self):
        # Block until the process exits
        stdout, stderr = self.mirror_process.communicate()
        
        exit_code = self.mirror_process.poll()
        self.log(f"[Mirror] Mirroring process ended. Exit Code: {exit_code}")
        
        if exit_code != 0 and stderr:
            clean_err = stderr.strip()
            self.log(f"[Error Info] {clean_err}")
            
        # Reset UI on main thread
        self.after(0, self.reset_mirroring_state)

    def stop_mirroring(self):
        if self.mirror_process:
            self.log("[Mirror] Stopping mirroring...")
            self.mirror_process.terminate()
            
        if hasattr(self, "demo_window") and self.demo_window is not None:
            self.log("[Demo] Stopping simulation...")
            try:
                self.demo_window.destroy()
            except:
                pass
            self.demo_window = None
            self.reset_mirroring_state()

    def run_demo_simulation(self):
        self.log("[Demo] Initializing simulated device...")
        
        # Disable buttons while active
        self.launch_btn.configure(text="STOP MIRRORING", fg_color="#ef4444", hover_color="#dc2626")
        self.scan_btn.configure(state="disabled")
        self.device_dropdown.configure(state="disabled")
        
        # Create the simulation window
        self.demo_window = ctk.CTkToplevel(self)
        window_title = "GlideCast: Demo_Simulation"
        self.demo_window.title(window_title)
        self.demo_window.geometry("380x680")
        self.demo_window.resizable(False, False)
        
        # Keep lock ratio and bring to front initially
        self.demo_window.attributes("-topmost", True)
        self.demo_window.after(100, lambda: self.demo_window.attributes("-topmost", False))
        
        # Handle manual close
        self.demo_window.protocol("WM_DELETE_WINDOW", self.stop_mirroring)
        
        # Draw demo content
        header_frame = ctk.CTkFrame(self.demo_window, height=30, corner_radius=0, fg_color="#1e293b")
        header_frame.pack(fill="x", side="top")
        
        time_label = ctk.CTkLabel(header_frame, text=time.strftime("%I:%M %p"), font=ctk.CTkFont(size=12, weight="bold"))
        time_label.pack(side="left", padx=15)
        
        status_label = ctk.CTkLabel(header_frame, text="LTE  🔋 100%", font=ctk.CTkFont(size=11))
        status_label.pack(side="right", padx=15)
        
        def update_clock():
            if hasattr(self, "demo_window") and self.demo_window is not None:
                try:
                    time_label.configure(text=time.strftime("%I:%M %p"))
                    self.demo_window.after(5000, update_clock)
                except:
                    pass
        update_clock()
        
        # Interactive Canvas
        self.demo_canvas = tk.Canvas(self.demo_window, bg="#0f172a", highlightthickness=0)
        self.demo_canvas.pack(fill="both", expand=True)
        
        # Draw background text
        self.demo_canvas.create_text(
            190, 150, 
            text="GLIDECAST", 
            fill="#06b6d4", 
            font=("Segoe UI", 24, "bold"),
            justify="center"
        )
        self.demo_canvas.create_text(
            190, 190, 
            text="DEVICE SIMULATION ACTIVE", 
            fill="#22d3ee", 
            font=("Segoe UI", 12, "bold"),
            justify="center"
        )
        
        info_text = (
            "This window simulates a connected phone screen.\n\n"
            "• Click/drag on this screen to test Mouse input\n"
            "• Type on your keyboard to test Keyboard input"
        )
        self.demo_canvas.create_text(
            190, 260,
            text=info_text,
            fill="#94a3b8",
            font=("Segoe UI", 11),
            width=300,
            justify="center"
        )
        
        # Text variables on canvas
        self.touch_text = self.demo_canvas.create_text(
            190, 360,
            text="Mouse: Click anywhere on this screen",
            fill="#10b981",
            font=("Consolas", 11),
            width=300,
            justify="center"
        )
        
        self.key_text = self.demo_canvas.create_text(
            190, 400,
            text="Keyboard: Press any key",
            fill="#f59e0b",
            font=("Consolas", 11),
            width=300,
            justify="center"
        )
        
        # Ripple effect for mouse clicks
        def on_canvas_click(event):
            try:
                self.demo_canvas.itemconfig(self.touch_text, text=f"Mouse: Click at ({event.x}, {event.y})")
                ripple = self.demo_canvas.create_oval(
                    event.x - 5, event.y - 5, 
                    event.x + 5, event.y + 5, 
                    outline="#22d3ee", width=2
                )
                def animate_ripple(size=5):
                    if hasattr(self, "demo_window") and self.demo_window is not None:
                        try:
                            self.demo_canvas.coords(
                                ripple, 
                                event.x - size, event.y - size, 
                                event.x + size, event.y + size
                            )
                            if size < 25:
                                self.demo_window.after(15, lambda: animate_ripple(size + 3))
                            else:
                                self.demo_canvas.delete(ripple)
                        except:
                            pass
                animate_ripple()
            except:
                pass
            
        self.demo_canvas.bind("<Button-1>", on_canvas_click)
        
        # Key log handler
        def on_key_press(event):
            try:
                key_name = event.keysym
                self.demo_canvas.itemconfig(self.key_text, text=f"Keyboard: Key '{key_name}' pressed")
            except:
                pass
            
        self.demo_window.bind("<Key>", on_key_press)
        
        # Apply custom icon to the demo window
        threading.Thread(target=self.apply_mirror_window_icon_thread, args=(window_title,), daemon=True).start()
        
        self.log("[Demo] Simulation window opened.")

    def reset_mirroring_state(self):
        self.mirror_process = None
        self.launch_btn.configure(text="START MIRRORING", fg_color="#0891b2", hover_color="#06b6d4")
        self.scan_btn.configure(state="normal")
        self.device_dropdown.configure(state="normal")
        self.start_device_scan()

    def on_closing(self):
        if self.mirror_process:
            try:
                self.mirror_process.terminate()
            except:
                pass
        self.destroy()

if __name__ == "__main__":
    app = GlideCastApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
