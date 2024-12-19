import os
import subprocess
import sys
import tkinter as tk
import time  # Import time to manage keypress delays
from tkinter import messagebox
from PIL import Image, ImageTk  # For image handling

class ThemeSelectorApp:
    def __init__(self, root, conf_dir="/boot/efi/EFI/Microsoft/Boot/refind.conf"):
        # Paths Relative to Project Root
        self.APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        self.THEMES_DIR = os.path.join(self.APP_ROOT, ".themes")  # Example: /path/to/project/.themes
        self.SAMPLE_DIR = os.path.join(self.APP_ROOT, "samples")
        self.DEFAULT_THEME_IMAGE = os.path.join(self.SAMPLE_DIR, "default.png")
        self.BG_FOLDER_NAME = "bg"  # The folder containing background images

        # the directory of the users refind configuration directory
        self.refind_conf_file = conf_dir

        self.root = root
        self.root.title("Win-integrated Linux (Ubuntu) rEFInd Automatic Skin Loader by GitHub  E.T.A.")
        self.root.geometry("800x500")
        self.root.minsize(600, 400)
        self.root.resizable(True, True)

        # Bind keys for navigation and deletion
        self.root.bind("<Up>", lambda e: self.handle_keypress(self.next_bg))
        self.root.bind("<Down>", lambda e: self.handle_keypress(self.prev_bg))
        self.root.bind("<Left>", lambda e: self.handle_keypress(self.prev_theme))
        self.root.bind("<Right>", lambda e: self.handle_keypress(self.next_theme))
        self.root.bind("<Delete>", lambda e: self.delete_theme())
        # Bind resizing events
        self.root.bind("<Configure>", self.on_resize)

        # get necessary permissions and validate necessary directories
        self.get_permission()
        self.check_dirs()

        # prevent the user from lagging the application by spamming any direction
        self.last_keypress_time = 0  # Track last keypress time
        self.debounce_delay = 0.2  # 200ms debounce delay

        # attributes for each theme
        self.themes = self.list_themes()
        self.theme_name = ''
        self.theme_dir = ''
        self.theme_index = 0

        # attributes for image background (if applicable)
        self.bg_images = None
        self.bg_name = ''
        self.bg_dir = None
        print(f'RESET: bg_dir {self.bg_dir}')
        self.bg_caption = None
        self.bg_index = 0  # Current background index

        # attributes for image
        self.current_image = ''
        self.current_image_name = ''
        self.current_image_dir = ''

        # widgets: labels
        self.image_label = tk.Label(self.root, bg="black")
        self.image_label.pack(fill="both", expand=True)
        self.theme_name_label = tk.Label(self.root, text="", font=("Helvetica", 16, "bold"), bg="black", fg="white")
        self.theme_name_label.pack(side="bottom", fill="x")

        # widgets: buttons
        self.left_button = tk.Button(self.root, text="◀", command=self.prev_theme, font=("Helvetica", 20), bg="#444", fg="white", relief=tk.FLAT)
        self.left_button.place(x=20, rely=0.5, anchor="w", width=50, height=50)
        self.right_button = tk.Button(self.root, text="▶", command=self.next_theme, font=("Helvetica", 20), bg="#444", fg="white", relief=tk.FLAT)
        self.right_button.place(relx=0.99, rely=0.5, anchor="e", width=50, height=50)

        self.display_theme()

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
        self.refind_conf_file = self.refind_conf_file
        return self.refind_conf_file

    def check_dirs(self):
        # Todo test this by restarting PC and checking app functionality
        """Ensure the themes directory and refind.conf exist."""

        # boolean shorthand
        config_found = os.path.exists(self.refind_conf_file)
        themes_found = os.path.exists(self.THEMES_DIR)

        if config_found and themes_found:
            return

        if not os.path.exists(self.THEMES_DIR):
            exit('Unable to locate themes directory!')

        # if passed/default refind config is not found, reinstall refind files
        if not os.path.exists(self.refind_conf_file):
            subprocess.check_call(['apt', 'install'])
            subprocess.check_call(['refind-install'])

        # if refind config files still can't be found after reinstall, ask user for dir
        if not os.path.exists(self.refind_conf_file):
            self.request_conf_dir()

        # Todo instead of crying about this being pointless, consider adding an option to drag config file onto app or
        # add a button to load it manually that disappears on load. A warning label can appear so the user can still
        # browse as per normal but they are aware that nothing is being set because the refind file couldn't be found

        # if user provides invalid path to the refind conf, this application cannot apply skins - pointless.
        if not os.path.exists(self.refind_conf_file):
            exit('Unable to locate the refind configuration file!')

    def update_config(self):
        """Edits the refind.conf to apply the selected theme."""
        if not os.path.exists(self.refind_conf_file):
            print(f"{self.refind_conf_file} not found. Creating a new one.")

        with open(self.refind_conf_file, 'r') as file:
            lines = file.readlines()

        print(f'Applying {self.theme_name} theme...')
        themes_query = 'include .themes/'
        bg_query = 'include background/'
        new_theme = f"{themes_query}{self.theme_name}/"

        if themes_query in lines[-2]:
            lines[-2] = new_theme
        elif themes_query in lines[-1]:
            lines[-1] = new_theme
        else:
            lines.append(new_theme)

        # if this configuration has a list of backgrounds...
        if self.bg_images:
            print('Applying background image...')
            new_bg = f'{bg_query}{self.bg_images[self.bg_index]}'
            # check the last line for a background parameter instead of unnecessarily looping
            if bg_query in lines[-1]:
                # if a bg parameter already exists, replace it
                lines[-1] = new_bg
            else:
                lines.append(new_bg)
        # else remove the old background selection parameter
        elif bg_query in lines[-1]:
            # remove the last line from the file (should be the bg param)
            lines.pop()

        # Todo remove this - just a test
        if bg_query in lines:
            print("If this image doesn't have backgrounds, something has gone wrong here...")

        # write the new data to the config file
        with open(self.refind_conf_file, 'w') as file:
            file.writelines(lines)

        print(f"Applied theme: {self.theme_name}")

    def list_themes(self):
        """Fetches the list of themes from the themes directory."""
        if not os.path.exists(self.THEMES_DIR):
            print("Themes directory does not exist. Creating...")
            os.makedirs(self.THEMES_DIR, exist_ok=True)

        # load the path of each theme in the themes directory into a python list for easier reference
        #themes = [d for d in os.listdir(self.ROOT_THEMES_DIR)]
        themes = os.listdir(self.THEMES_DIR)

        if not themes:
            exit('No themes found in the directory.')

        print(f'List size: {len(themes)}')
        return themes

    def get_image_dir(self):
        """Returns the path to the theme's image or a fallback."""
        screenshot_path = os.path.join(self.SAMPLE_DIR, f'{self.theme_name}.png')
        background_path = os.path.join(self.THEMES_DIR, 'background.png')

        print(f'CHECK: self.bg_images = {self.bg_images}')
        # if the path leads to a folder of images
        if self.bg_images:
            self.bg_dir = os.path.join(self.THEMES_DIR, self.BG_FOLDER_NAME)
            print(f'SET1: bg_dir {self.bg_dir}')
            return self.bg_images[self.bg_index]
        elif os.path.exists(screenshot_path):
            return screenshot_path
        elif os.path.exists(background_path):
            return background_path
        else:
            print(f"No image found for theme: {self.theme_name}, using fallback image.")
            return self.DEFAULT_THEME_IMAGE  # Default image fallback

    def get_bg_images(self):
        print(f'Attempting to get background images... self.bg_dir = {self.bg_dir}')
        self.bg_dir = os.path.join(self.theme_dir, self.BG_FOLDER_NAME)
        # if the current theme has multiple backgrounds
        if os.path.isdir(self.bg_dir):
            # return a list of strings containing the directory to each background
            self.bg_images = os.listdir(self.bg_dir)
            print(f'SET: self.bg_images = {self.bg_images}')
        else:
            print('No background images found.')
            self.bg_refresh_attributes()

        return self.bg_images

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
        self.update_bg_caption()

    def update_bg_caption(self):
        """Update the caption for the current background index."""
        pass
        # if hasattr(self, 'bg_caption') and self.bg_images:
        #     self.bg_caption.config(text=f"Background {self.bg_index + 1}/{len(self.bg_images)}")

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

    def bg_refresh_attributes(self):
        self.bg_name = ''
        self.bg_dir = ''
        print(f'RESET: bg_dir {self.bg_dir}')
        self.bg_index = 0
        self.bg_images = None

    def display_theme(self):
        if not self.themes:
            messagebox.showerror("Error", "No themes available.")
            return

        # set current theme
        self.theme_name = self.themes[self.theme_index]
        self.theme_dir = os.path.join(self.THEMES_DIR, self.theme_name)
        self.current_image_name = self.theme_name.title()
        self.current_image_dir = self.get_image_dir()
        self.bg_images = self.get_bg_images()

        # Show or hide up/down arrows and caption
        if self.bg_images:
            self.current_image_dir = self.bg_images[self.bg_index]
            self.current_image_name += f' {self.bg_index + 1}/{len(self.bg_images)}'
            self.image_label.config(text=f"{self.bg_index + 1}/{len(self.bg_images)}")
            self.show_bg_navigation()
        else:
            self.hide_bg_navigation()

        # Update image and write changes to config file
        self.update_image()
        self.update_config()

    def update_image(self):
        if os.path.exists(self.current_image_dir):
            try:
                window_width = self.root.winfo_width()
                window_height = self.root.winfo_height() - 50

                image = Image.open(self.current_image_dir)
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

                self.current_image = ImageTk.PhotoImage(final_image)
                self.image_label.config(image=self.current_image)
                self.theme_name_label.config(text=self.current_image_name)
                self.update_bg_caption()

            except Exception as e:
                print(f"Error resizing image: {e}")

    def next_theme(self):
        if self.themes:
            self.theme_index = (self.theme_index + 1) % len(self.themes)
            self.bg_refresh_attributes()
            self.display_theme()

    def prev_theme(self):
        if self.themes:
            self.theme_index = (self.theme_index - 1) % len(self.themes)
            self.bg_refresh_attributes()
            self.display_theme()

    def next_bg(self):
        print(f'Attempt to set next background... self.bg_images = {self.bg_images}')
        if self.bg_images:
            self.bg_index = (self.bg_index + 1) % len(self.bg_images)
            self.current_image_dir = self.get_image_dir()
            self.display_theme()

    def prev_bg(self):
        print(f'Attempt to set previous background... self.bg_images = {self.bg_images}')
        if self.bg_images:
            self.bg_index = (self.bg_index - 1) % len(self.bg_images)
            self.display_theme()

    def delete_theme(self):
        if not self.themes:
            messagebox.showerror("Error", "No themes available to delete.")
            return

        theme_to_delete = self.themes[self.theme_index]
        confirm = messagebox.askyesno("Delete Theme", f"Are you sure you want to delete the theme '{theme_to_delete}'?")
        if confirm:
            theme_path = os.path.join(self.THEMES_DIR, theme_to_delete)
            try:
                # Delete the theme folder
                import shutil
                shutil.rmtree(theme_path)
                messagebox.showinfo("Success", f"Theme '{theme_to_delete}' deleted successfully.")

                # Refresh the themes list
                self.themes = self.list_themes()
                if self.themes:
                    # update current index to 0 if there is only one item left, else se
                    self.theme_index = (self.theme_index - 1) % len(self.themes)
                    self.display_theme()
                else:
                    self.theme_name_label.config(text="")
                    self.image_label.config(image="")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete theme '{theme_to_delete}': {e}")

if __name__ == "__main__":
    base_gui = tk.Tk()
    app = ThemeSelectorApp(base_gui)
    app.root.mainloop()
