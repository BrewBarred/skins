import os
import subprocess
import sys
import tkinter as tk
import time  # Import time to manage keypress delays
from tkinter import messagebox
from PIL import Image, ImageTk  # For image handling

class ThemeSelectorApp():
    def __init__(self, root):
        # Paths Relative to Project Root
        self.APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        self.refind_conf_dir = os.path.join(os.path., "logs.txt")
        self.THEME_DIR = os.path.join(self.APP_ROOT, ".themes")  # Example: /path/to/project/.themes
        self.SAMPLE_DIR = os.path.join(self.APP_ROOT, "samples")
        self.DEFAULT_THEME_IMAGE = os.path.join(self.SAMPLE_DIR, "default.png")
        self.BG_FOLDER_NAME = "bg"  # The folder containing background images

        self.root = root
        self.root.title("rEFInd Skin Selector")
        self.root.geometry("800x500")
        self.root.minsize(600, 400)
        self.root.resizable(True, True)

        # get necessary permissions and validate necessary directories
        self.get_permission()
        self.check_dirs()

        self.themes = self.list_themes()
        self.current_theme_dir = ''
        self.bg_images = self.get_bg_images()  # List of background images
        self.current_bg_index = 0  # Current background index
        self.current_index = 0

        self.last_keypress_time = 0  # Track last keypress time
        self.debounce_delay = 0.2  # 200ms debounce delay

        # Bind keys for navigation and deletion
        self.root.bind("<Up>", lambda e: self.handle_keypress(self.next_bg))
        self.root.bind("<Down>", lambda e: self.handle_keypress(self.prev_bg))
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

    def exit(self, exit_msg, sleep=3):
        # Todo make static?
        print(exit_msg)
        time.sleep(sleep)
        sys.exit(0)

    # Ensure the script is running with sudo privileges
    def get_permission(self):
        if os.geteuid() != 0:
            print("Root privileges are required. Attempting to relaunch as root...")
            try:
                subprocess.check_call(['sudo', sys.executable] + sys.argv)
            except subprocess.CalledProcessError:
                exit("Failed to gain root privileges. Exiting.")
            # Todo check if this is needed? Does it close the lowered terminal instance, perhaps?
            sys.exit(0)

    def request_conf_dir(self):
        # request the refind configuration file directory from the user using an open file dialog
        # Todo add open file dialog - LOL
        self.refind_conf_dir = self.refind_conf_dir
        return self.refind_conf_dir

    def check_dirs(self):
        # Todo test this by restarting PC and checking app functionality
        """Ensure the themes directory and refind.conf exist."""
        os.makedirs(self.THEME_DIR, exist_ok=True)
        if not os.path.exists(self.refind_conf_dir):
            self.request_conf_dir()
            if not self.refind_conf_dir:
                exit('Unable to find refind configuration file!')

    def update_logs(self, theme_name):
        """Edits the refind.conf to apply the selected theme."""
        if not os.path.exists(self.refind_conf_dir):
            print(f"{self.refind_conf_dir} not found. Creating a new one.")
            with open(self.refind_conf_dir, 'w') as file:
                file.write(f"Failed to find log file at path: {self.refind_conf_dir}. Logs may have been deleted\n")
            return

        with open(self.refind_conf_dir, 'r') as file:
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

        with open(self.refind_conf_dir, 'w') as file:
            file.writelines(lines)

        print(f"Applied theme: {theme_name}")

    def list_themes(self):
        """Fetches the list of themes from the themes directory."""
        if not os.path.exists(self.THEME_DIR):
            print("Themes directory does not exist. Creating...")
            os.makedirs(self.THEME_DIR, exist_ok=True)
        themes = [d for d in os.listdir(self.THEME_DIR)
                  if not 'default' in d.lower() and os.path.isdir(os.path.join(self.THEME_DIR, d))]
        if not themes:
            print("No themes found in the directory.")
        print(f'List size: {len(themes)}')
        return themes

    def get_theme_image(self, theme):
        """Returns the path to the theme's image or a fallback."""
        screenshot_path = os.path.join(self.SAMPLE_DIR, f'{theme}.png')
        background_path = os.path.join(self.THEME_DIR, 'background.png')

        if os.path.exists(screenshot_path):
            return screenshot_path
        elif os.path.exists(background_path):
            return background_path
        else:
            print(f"No image found for theme: {theme}, using fallback image.")
            return self.DEFAULT_THEME_IMAGE  # Default image fallback

    def get_bg_images(self):
        if os.path.exists(self.bg_dir):
            return [os.path.join(self.bg_dir, f) for f in sorted(os.listdir(self.bg_dir)) if f.endswith('.png')]

    def show_bg_navigation(self):
        """Show the up/down arrows and caption when backgrounds exist."""
        self.root.bind("<Up>", lambda e: self.handle_keypress(self.next_bg))
        self.root.bind("<Down>", lambda e: self.handle_keypress(self.prev_bg))

        if not hasattr(self, 'bg_caption'):  # Create bg_caption if it doesn't exist
            self.bg_caption = tk.Label(self.root, text="", font=("Helvetica", 12), bg="black", fg="white")
            self.bg_caption.place(relx=0.95, rely=0.95, anchor="se")

        self.update_bg_caption()

    def hide_bg_navigation(self):
        """Hide the up/down arrows and caption when backgrounds don't exist."""
        self.root.unbind("<Up>")
        self.root.unbind("<Down>")

        if hasattr(self, 'bg_caption'):
            self.bg_caption.place_forget()

    def update_bg_caption(self):
        """Update the caption for the current background index."""
        if hasattr(self, 'bg_caption') and self.bg_images:
            self.bg_caption.config(text=f"Background {self.current_bg_index + 1}/{len(self.bg_images)}")

    ############ OLD CLASS START #############

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

        # Set current theme
        self.current_theme_name = self.themes[index]
        self.current_image_path = self.get_theme_image(self.current_theme_name)

        # Update image and caption
        self.update_image()
        self.theme_name_label.config(text=self.current_theme_name.title())

        # Check for bg images
        self.bg_images = self.get_bg_images()  # Refresh bg_images for the current theme
        self.current_bg_index = 0  # Reset bg index

        # Show or hide up/down arrows and caption
        if self.bg_images and len(self.bg_images) > 1:
            self.show_bg_navigation()
            self.display_bg(self.current_bg_index)
        else:
            self.hide_bg_navigation()

        self.update_logs(self.current_theme_name)

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

    def display_bg(self, index):
        if self.bg_images:
            self.update_image()
            self.current_bg_index.config(text=f"Background {index + 1}/{len(self.bg_images)}")

    def next_theme(self):
        if self.themes:
            self.current_index = (self.current_index + 1) % len(self.themes)
            self.display_theme(self.current_index)

    def prev_theme(self):
        if self.themes:
            self.current_index = (self.current_index - 1) % len(self.themes)
            self.display_theme(self.current_index)

    def next_bg(self):
        if self.bg_images:
            self.current_bg_index = (self.current_bg_index + 1) % len(self.bg_images)
            self.display_bg(self.current_bg_index)
            self.update_bg_caption()

    def prev_bg(self):
        if self.bg_images:
            self.current_bg_index = (self.current_bg_index - 1) % len(self.bg_images)
            self.display_bg(self.current_bg_index)
            self.update_bg_caption()

    def delete_theme(self):
        if not self.themes:
            messagebox.showerror("Error", "No themes available to delete.")
            return

        theme_to_delete = self.themes[self.current_index]
        confirm = messagebox.askyesno("Delete Theme", f"Are you sure you want to delete the theme '{theme_to_delete}'?")
        if confirm:
            theme_path = os.path.join(self.THEME_DIR, theme_to_delete)
            try:
                # Delete the theme folder
                import shutil
                shutil.rmtree(theme_path)
                messagebox.showinfo("Success", f"Theme '{theme_to_delete}' deleted successfully.")

                # Refresh the themes list
                self.themes = self.list_themes()
                if self.themes:
                    self.current_index = self.current_index % len(self.themes)
                    self.display_theme(self.current_index)
                else:
                    self.theme_name_label.config(text="")
                    self.image_label.config(image="")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete theme '{theme_to_delete}': {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ThemeSelectorApp(root)
    app.root.mainloop()
