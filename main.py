import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import re
import os
import sys
import subprocess
import yt_dlp
import json

# Try to import VLC with better error handling
try:
    import vlc
    has_vlc = True
except (ImportError, OSError) as e:
    has_vlc = False
    vlc_error_message = str(e)

def check_dependencies():
    """Check if all dependencies are installed and up to date."""
    try:
        # Try to ensure yt-dlp is installed
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Check if VLC is installed on the system
        if not has_vlc:
            print("VLC Python bindings not found or not working properly.")
            print(f"Error: {vlc_error_message}")
            print("Attempting to install python-vlc...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "python-vlc"], 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
        return True
    except Exception as e:
        print(f"Failed to update dependencies: {e}")
        return False

class YouTubeAudioStreamer:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Audio Streamer")
        self.root.geometry("550x280")  # Slightly reduced size for minimalism
        self.root.resizable(True, True)
        
        # Variables
        self.url_var = tk.StringVar()
        self.is_playing = False
        self.player = None
        self.media = None
        
        # URL persistence variables
        self.saved_urls = []
        self.urls_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_urls.json")
        
        # Set up dark theme
        self.setup_dark_theme()
        
        # Create GUI elements
        self.setup_ui()
        
        # Load saved URLs
        self.load_saved_urls()
    
    def setup_dark_theme(self):
        """Configure dark theme for the application"""
        style = ttk.Style()
        
        # Configure colors
        bg_color = "#1e1e1e"  # Dark background
        fg_color = "#e0e0e0"  # Light text
        accent_color = "#3a3a3a"  # Slightly lighter background for contrast
        select_color = "#0066cc"  # Selection color
        
        # Configure ttk theme
        style.theme_use('default')  # Start with default theme as base
        
        # Configure common elements
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TButton', background=accent_color, foreground=fg_color, borderwidth=0)
        style.map('TButton', 
                 background=[('active', '#4a4a4a'), ('pressed', '#5a5a5a')],
                 foreground=[('active', '#ffffff')])
        
        # Create a special style for the multi-function button
        style.configure('Play.TButton', 
                       background=accent_color, 
                       foreground=fg_color, 
                       borderwidth=0,
                       font=('TkDefaultFont', 10, 'bold'))
        style.map('Play.TButton',
                 background=[('active', '#4a4a4a'), ('pressed', '#5a5a5a')],
                 foreground=[('active', '#ffffff')])
        
        style.configure('TEntry', 
                       fieldbackground=accent_color, 
                       foreground=fg_color,
                       insertcolor=fg_color,  # Cursor color
                       borderwidth=0)
        
        # Configure combobox
        style.configure('TCombobox', 
                       fieldbackground=accent_color,
                       background=bg_color,
                       foreground=fg_color,
                       arrowcolor=fg_color,
                       borderwidth=0)
        style.map('TCombobox',
                 fieldbackground=[('readonly', accent_color)],
                 foreground=[('readonly', fg_color)])
        
        # Configure scale (slider)
        style.configure('TScale',
                       background=bg_color,
                       troughcolor=accent_color,
                       sliderrelief='flat')
        
        # Configure separator
        style.configure('TSeparator', background='#3a3a3a')
        
        # Configure root window
        self.root.configure(bg=bg_color)
        
    def setup_ui(self):
        # Main container with minimal padding
        main_container = ttk.Frame(self.root, padding="8")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # URL section - simplified without LabelFrame
        url_section = ttk.Frame(main_container)
        url_section.pack(fill=tk.X, pady=(0, 8))
        
        # Small label
        ttk.Label(url_section, text="URL").pack(side=tk.LEFT, padx=(0, 5))
        
        # URL entry with clean look
        url_entry = ttk.Entry(url_section, textvariable=self.url_var)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        url_entry.focus_set()
        
        # Saved URLs section - simplified UI
        saved_section = ttk.Frame(main_container)
        saved_section.pack(fill=tk.X, pady=(0, 8))
        
        # Dropdown for saved URLs
        self.saved_urls_var = tk.StringVar()
        self.saved_urls_dropdown = ttk.Combobox(saved_section, textvariable=self.saved_urls_var, state="readonly")
        self.saved_urls_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.saved_urls_dropdown.bind("<<ComboboxSelected>>", self.load_selected_url)
        
        # Minimal buttons for URL management
        save_btn = ttk.Button(saved_section, text="+", command=self.save_current_url, width=2)
        save_btn.pack(side=tk.LEFT, padx=1)
        self.create_tooltip(save_btn, "Save current URL")
        
        delete_btn = ttk.Button(saved_section, text="−", command=self.delete_selected_url, width=2)
        delete_btn.pack(side=tk.LEFT, padx=1)
        self.create_tooltip(delete_btn, "Delete selected URL")
        
        # Playback controls - clean minimal design with single button
        control_section = ttk.Frame(main_container)
        control_section.pack(fill=tk.X, pady=(0, 8))
        
        # Play/Stop Button (removed pause functionality)
        self.play_button = ttk.Button(control_section, text="▶", command=self.toggle_playback, 
                                      width=4, style='Play.TButton')
        self.play_button.pack(side=tk.LEFT, padx=(0, 8))
        self.create_tooltip(self.play_button, "Play/Stop")
        
        # Volume slider - simplified design
        self.volume_var = tk.IntVar(value=100)
        self.volume_slider = ttk.Scale(control_section, from_=0, to=100, orient=tk.HORIZONTAL, 
                                      variable=self.volume_var, command=self.set_volume)
        self.volume_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Simple volume indicator
        volume_value = ttk.Label(control_section, textvariable=self.volume_var, width=3)
        volume_value.pack(side=tk.LEFT, padx=(4, 0))
        
        # Status bar - minimal design
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                                   anchor=tk.W, padding=(4, 2))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Add a subtle separator
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(side=tk.BOTTOM, fill=tk.X, pady=2)

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def show_tooltip(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create a toplevel window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            # Dark-themed tooltip
            label = ttk.Label(self.tooltip, text=text, background="#333333", foreground="#ffffff", 
                             relief=tk.SOLID, borderwidth=1, padding=(3, 2))
            label.pack()
            
        def hide_tooltip(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def is_valid_youtube_url(self, url):
        # Basic YouTube URL validation
        youtube_regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+'
        return bool(re.match(youtube_regex, url))
        
    def update_ui_playing(self, title=None):
        self.play_button.config(text="■")  # Change to stop symbol instead of pause
        self.flash_status(f"Playing: {title}" if title else "Playing", "success")
        self.is_playing = True
    
    def stop_playback(self):
        if self.player:
            self.player.stop()
            self.player = None
            self.media = None
            self.is_playing = False
            self.play_button.config(text="▶")  # Change text back to play symbol
            self.flash_status("Stopped")

    def toggle_playback(self):
        url = self.url_var.get().strip()
        
        if self.is_playing:
            # Playing - so stop (removed pause functionality)
            self.stop_playback()
            return
            
        # Not playing, so start playback
        if not url:
            self.flash_status("Please enter a YouTube URL", "error")
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
            
        if not self.is_valid_youtube_url(url):
            self.flash_status("Invalid YouTube URL", "error")
            messagebox.showerror("Error", "Invalid YouTube URL")
            return
            
        # Start new playback
        self.status_var.set("Loading stream...")
        self.root.update()
        self.play_button.config(state=tk.DISABLED)  # Disable during loading
        threading.Thread(target=self.start_playback, args=(url,), daemon=True).start()

    def flash_status(self, message, level="info"):
        """Flash a status message with color indication"""
        if level == "error":
            self.status_bar.configure(foreground="#ff6b6b")  # Softer red for dark theme
        elif level == "success":
            self.status_bar.configure(foreground="#4caf50")  # Softer green for dark theme
        else:
            self.status_bar.configure(foreground="#e0e0e0")  # Default light text
            
        self.status_var.set(message)
        
        # Reset color after 3 seconds
        self.root.after(3000, lambda: self.status_bar.configure(foreground="#e0e0e0"))
    
    def start_playback(self, url):
        try:
            # Get best audio stream using yt-dlp
            ydl_opts = {
                'format': 'bestaudio',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            self.root.after(0, lambda: self.status_var.set("Extracting audio stream..."))
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info['url']
                title = info.get('title', 'Unknown Title')
            
            self.root.after(0, lambda: self.status_var.set("Connecting to stream..."))
            
            # Create VLC instance and player with better error handling
            try:
                # Try to initialize VLC with explicit path to DLL/shared library if needed
                if sys.platform.startswith('linux'):
                    # Try common locations for libvlc on Linux
                    vlc_paths = [
                        '/usr/lib/x86_64-linux-gnu/libvlc.so',
                        '/usr/lib/i386-linux-gnu/libvlc.so',
                        '/usr/lib/libvlc.so',
                        '/usr/local/lib/libvlc.so'
                    ]
                    for path in vlc_paths:
                        if os.path.exists(path):
                            instance = vlc.Instance('--no-xlib', '--quiet', f'--plugin-path={os.path.dirname(path)}/../vlc/plugins')
                            break
                    else:
                        instance = vlc.Instance('--no-xlib', '--quiet')
                else:
                    instance = vlc.Instance('--quiet')
                
                self.player = instance.media_player_new()
                self.media = instance.media_new(stream_url)
                self.player.set_media(self.media)
                
                # Set volume
                self.player.audio_set_volume(self.volume_var.get())
                
                # Start playing
                self.player.play()
                
                # Update UI
                self.root.after(0, lambda: self.update_ui_playing(title))
            except Exception as vlc_error:
                raise Exception(f"VLC error: {str(vlc_error)}. Make sure VLC media player is installed on your system.")
            
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda message=error_message: self.show_error(message))
        finally:
            self.root.after(0, lambda: self.play_button.config(state=tk.NORMAL))  # Re-enable button
    
    def show_error(self, error_msg):
        self.flash_status(f"Error: {error_msg}", "error")
        messagebox.showerror("Error", f"Failed to play stream: {error_msg}")
        self.is_playing = False
        self.play_button.config(text="▶")  # Fix: remove "Play" text
    
    def load_saved_urls(self):
        """Load saved URLs from file"""
        if os.path.exists(self.urls_file):
            try:
                with open(self.urls_file, 'r') as f:
                    self.saved_urls = json.load(f)
                    self.update_urls_dropdown()
            except Exception as e:
                print(f"Error loading saved URLs: {e}")
                self.saved_urls = []
        else:
            self.saved_urls = []
            self.update_urls_dropdown()
            
    def update_urls_dropdown(self):
        """Update the dropdown with saved URLs"""
        if self.saved_urls:
            self.saved_urls_dropdown['values'] = self.saved_urls
        else:
            self.saved_urls_dropdown['values'] = ["No saved URLs"]
            
    def save_urls_to_file(self):
        """Save URLs to file"""
        try:
            with open(self.urls_file, 'w') as f:
                json.dump(self.saved_urls, f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save URLs: {e}")
            
    def save_current_url(self):
        """Save the current URL to the list with a name"""
        url = self.url_var.get().strip()
        if not url:
            self.flash_status("Please enter a YouTube URL", "error")
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
            
        if not self.is_valid_youtube_url(url):
            self.flash_status("Invalid YouTube URL", "error")
            messagebox.showerror("Error", "Invalid YouTube URL")
            return
            
        # Ask for a name for the URL
        name = simpledialog.askstring("Save URL", "Enter a name for this URL:", parent=self.root)
        if not name:
            return
        
        # Simple format without categories
        saved_entry = f"{name} - {url}"
            
        if saved_entry not in self.saved_urls:
            self.saved_urls.append(saved_entry)
            self.save_urls_to_file()
            self.update_urls_dropdown()
            self.flash_status(f"URL saved as '{name}'", "success")
        else:
            self.flash_status("This URL is already saved", "info")
            messagebox.showinfo("Info", "This URL is already saved")

    def load_selected_url(self, event=None):
        """Load the selected URL from dropdown"""
        selected = self.saved_urls_var.get()
        if selected and "No saved URLs" not in selected:
            try:
                # Simple format: Name - URL
                url = selected.split(" - ", 1)[1]
                self.url_var.set(url)
                self.flash_status(f"Loaded: {selected.split(' - ', 1)[0]}")
            except IndexError:
                pass

    def delete_selected_url(self):
        """Delete the selected URL from saved list"""
        selected = self.saved_urls_var.get()
        if selected and "No saved URLs" not in selected:
            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete '{selected}'?"):
                self.saved_urls.remove(selected)
                self.save_urls_to_file()
                self.update_urls_dropdown()
                self.flash_status(f"Deleted: {selected.split(' - ', 1)[0]}", "info")
                # Clear the selection
                self.saved_urls_var.set("")
        else:
            self.flash_status("No URL selected", "error")

    def set_volume(self, *args):
        """Set the volume of the player based on the slider value"""
        if self.player:
            self.player.audio_set_volume(self.volume_var.get())

if __name__ == "__main__":
    # Check dependencies
    check_dependencies()
    
    # Create the root window
    root = tk.Tk()
    
    # Apply a theme
    style = ttk.Style()
    try:
        style.theme_use("clam")  # Using a modern theme if available
    except:
        pass  # Use default theme if modern theme not available
    
    # Create the application
    app = YouTubeAudioStreamer(root)
    
    # Start the mainloop
    root.mainloop()