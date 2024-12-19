import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk  # For image handling

# Paths Relative to Project Root
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
REFIND_CONF = os.path.join(APP_ROOT, "refind.conf")
THEME_DIR = os.path.join(APP_ROOT, ".themes")  # Example: /path/to/project/.themes
SAMPLE_DIR = os.path.join(APP_ROOT, "samples")
DEFAULT_THEME_IMAGE = os.path.join(SAMPLE_DIR, "default.png")

def main():
    check_root()
    ensure_theme_directory()
    root = tk.Tk()
    app = ThemeSelectorApp(root)
    app.root.mainloop()

# Ensure the script is running with sudo privileges
def check_root():
    if os.geteuid() != 0:
        print("Root privileges are required. Re-running the script with sudo...")
        try:
            subprocess.check_call(['sudo', sys.executable] + sys.argv)
        except subprocess.CalledProcessError:
            print("Failed to gain root privileges. Exiting.")
            exit(1)
        sys.exit(0)

def ensure_theme_directory():
    """Ensure the themes directory and refind.conf exist."""
    os.makedirs(THEME_DIR, exist_ok=True)
    if not os.path.exists(REFIND_CONF):
        with open(REFIND_CONF, 'w') as file:
            file.write("# rEFInd theme configuration\n")

def update_refind_conf(theme_name):
    """Edits the refind.conf to apply the selected theme."""
    if not os.path.exists(REFIND_CONF):
        print(f"{REFIND_CONF} not found. Creating a new one.")
        with open(REFIND_CONF, 'w') as file:
            file.write(f"include .themes/{theme_name}/\n")  # Add a default include line
        return

    with open(REFIND_CONF, 'r') as file:
        lines = file.readlines()

    # Replace or append the theme include line
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith("include .themes/"):
            lines[i] = f"include .themes/{theme_name}/\n"
            updated = True
            break

    if not updated:
        lines.append(f"include .themes/{theme_name}/\n")

    with open(REFIND_CONF, 'w') as file:
        file.writelines(lines)

    print(f"Applied theme: {theme_name}")

def list_themes():
    """Fetches the list of themes from the themes directory."""
    if not os.path.exists(THEME_DIR):
        print("Themes directory does not exist. Creating...")
        os.makedirs(THEME_DIR, exist_ok=True)
    themes = [d for d in os.listdir(THEME_DIR) if not 'default' in d.lower() and os.path.isdir(os.path.join(THEME_DIR, d))]
    if not themes:
        print("No themes found in the directory.")
    print(f'List size: {len(themes)}')
    return themes

def get_theme_image(theme):
    """Returns the path to the theme's image or a fallback."""
    theme_path = os.path.join(THEME_DIR, theme)
    screenshot_path = os.path.join(theme_path, 'screenshot.png')
    background_path = os.path.join(theme_path, 'background.png')

    if os.path.exists(screenshot_path):
        return screenshot_path
    elif os.path.exists(background_path):
        return background_path
    else:
        print(f"No image found for theme: {theme}, using fallback image.")
        return DEFAULT_THEME_IMAGE  # Default image fallback

def get_icon_positions(theme):
    """Fetches icon positions by checking all .conf files in theme's directory."""
    positions = []
    theme_dir = os.path.join(THEME_DIR, theme)

    for root, _, files in os.walk(theme_dir):
        for file in files:
            if file.endswith(".conf"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    for line in f:
                        if line.strip().startswith("icon"):
                            parts = line.split()
                            if len(parts) == 4:
                                try:
                                    x = int(parts[1])
                                    y = int(parts[2])
                                    icon_file = parts[3].strip()
                                    positions.append((x, y, icon_file))
                                except ValueError:
                                    print(f"Invalid icon position in {file_path}: {line.strip()}")
    return positions

import time  # Import time to manage keypress delays

class ThemeSelectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("rEFInd Skin Selector")
        self.root.geometry("800x500")
        self.root.minsize(600, 400)
        self.root.resizable(True, True)

        self.themes = list_themes()
        self.current_index = 0
        self.last_keypress_time = 0  # Track last keypress time
        self.debounce_delay = 0.2  # 200ms debounce delay

        # Bind keys for navigation and deletion
        self.root.bind("<Left>", lambda e: self.handle_keypress(self.prev_theme))
        self.root.bind("<Right>", lambda e: self.handle_keypress(self.next_theme))
        self.root.bind("<Delete>", lambda e: self.delete_theme())

        # Bind resizing events
        self.root.bind("<Configure>", self.on_resize)

        # Widgets
        self.image_label = tk.Label(self.root, bg="black")
        self.image_label.pack(fill="both", expand=True)

        self.theme_name_label = tk.Label(self.root, text="", font=("Helvetica", 16, "bold"), bg="black", fg="white")
        self.theme_name_label.pack(side="bottom", fill="x")

        self.left_button = tk.Button(self.root, text="◀", command=self.prev_theme, font=("Helvetica", 20), bg="#444", fg="white", relief=tk.FLAT)
        self.left_button.place(x=20, rely=0.5, anchor="w", width=50, height=50)

        self.right_button = tk.Button(self.root, text="▶", command=self.next_theme, font=("Helvetica", 20), bg="#444", fg="white", relief=tk.FLAT)
        self.right_button.place(relx=0.99, rely=0.5, anchor="e", width=50, height=50)

        self.photo = None
        self.display_theme(self.current_index)

    def is_keypress_allowed(self):
        """Check if enough time has passed since the last keypress."""
        current_time = time.time()
        if current_time - self.last_keypress_time >= self.debounce_delay:
            self.last_keypress_time = current_time
            return True
        return False

    def handle_keypress(self, action):
        """Throttle keypresses to avoid rapid switching."""
        if self.is_keypress_allowed():
            action()

    def on_resize(self, event):
        self.update_image()

    def display_theme(self, index):
        if not self.themes:
            messagebox.showerror("Error", "No themes available.")
            return
        self.current_theme_name = self.themes[index]
        self.current_image_path = get_theme_image(self.current_theme_name)
        self.update_image()
        self.theme_name_label.config(text=self.current_theme_name.title())
        update_refind_conf(self.current_theme_name)

    def update_image(self):
        if os.path.exists(self.current_image_path):
            try:
                window_width = self.root.winfo_width()
                window_height = self.root.winfo_height() - 50

                image = Image.open(self.current_image_path)
                img_ratio = image.width / image.height
                window_ratio = window_width / window_height

                if img_ratio > window_ratio:
                    new_width = window_width
                    new_height = int(new_width / img_ratio)
                else:
                    new_height = window_height
                    new_width = int(new_height * img_ratio)

                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                final_image = Image.new("RGB", (window_width, window_height), (0, 0, 0))
                paste_x = (window_width - new_width) // 2
                paste_y = (window_height - new_height) // 2
                final_image.paste(resized_image, (paste_x, paste_y))

                self.photo = ImageTk.PhotoImage(final_image)
                self.image_label.config(image=self.photo)
            except Exception as e:
                print(f"Error resizing image: {e}")

    def next_theme(self):
        if self.themes:
            self.current_index = (self.current_index + 1) % len(self.themes)
            self.display_theme(self.current_index)

    def prev_theme(self):
        if self.themes:
            self.current_index = (self.current_index - 1) % len(self.themes)
            self.display_theme(self.current_index)

    def delete_theme(self):
        if not self.themes:
            messagebox.showerror("Error", "No themes available to delete.")
            return

        theme_to_delete = self.themes[self.current_index]
        confirm = messagebox.askyesno("Delete Theme", f"Are you sure you want to delete the theme '{theme_to_delete}'?")
        if confirm:
            theme_path = os.path.join(THEME_DIR, theme_to_delete)
            try:
                # Delete the theme folder
                import shutil
                shutil.rmtree(theme_path)
                messagebox.showinfo("Success", f"Theme '{theme_to_delete}' deleted successfully.")

                # Refresh the themes list
                self.themes = list_themes()
                if self.themes:
                    self.current_index = self.current_index % len(self.themes)
                    self.display_theme(self.current_index)
                else:
                    self.theme_name_label.config(text="")
                    self.image_label.config(image="")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete theme '{theme_to_delete}': {e}")


if __name__ == "__main__":
    main()