import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
import time  # Import time to manage keypress delays
from tkinter import messagebox
from PIL import Image, ImageTk  # For image handling

class ThemeSelectorApp:
    def __init__(self, root, refind_root=None):
        print('Launching skin selector...')
        self.REFIND_ROOT = refind_root if refind_root else "/boot/efi/EFI/refind"
        self.REFIND_THEME_ROOT = os.path.join(self.REFIND_ROOT, "theme")
        # Paths Relative to Project Root
        self.APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        self.APP_THEMES_ROOT = os.path.join(self.APP_ROOT, ".themes")  # Example: /path/to/project/.themes
        self.SAMPLE_ROOT = os.path.join(self.APP_THEMES_ROOT, "samples")
        self.ERROR_IMAGE = os.path.join(self.SAMPLE_ROOT, ".error.png")
        self.BG_FOLDER_NAME = "bg"  # The folder containing background images

        self.root = root
        self.root.title("Linux rEFInd Automatic Skin Loader by E.T.A. and skin authors")
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

        # prevent the user from lagging the application by spamming any direction
        self.last_keypress_time = 0  # Track last keypress time
        self.debounce_delay = 0.2  # 200ms debounce delay

        # attributes for each theme
        self.themes = self.list_themes()
        self.theme_name = ''
        self.theme_dir = ''
        self.theme_index = 0
        self.theme_config_file = ''

        # attributes for image background (if applicable)
        self.bg_name = ''
        self.bg_images = None
        self.bg_dir = None
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

    def refind_root(self):
        """
        Get or set refind root (TODO)
        :return:
        """
        # request the refind configuration file directory from the user using an open file dialog
        # Todo add open file dialog - LOL
        return self.REFIND_ROOT

    def check_dirs(self):
        # Todo test this by restarting PC and checking app functionality
        """Ensure the themes directory and refind.conf exist."""

        # boolean shorthand
        conf_found = os.path.exists(self.theme_config_file)
        themes_found = os.path.exists(self.APP_THEMES_ROOT)
        print(f'\nConfig: {self.REFIND_ROOT}\nApp themes: {self.APP_THEMES_ROOT}')

        if conf_found and themes_found:
            return

        print('\nUnable to find launch files... attempting to install...\n')

        if not os.path.exists(self.APP_THEMES_ROOT):
            exit('Unable to locate themes directory!')

        # if passed/default refind config is not found, reinstall refind files
        if not os.path.exists(self.REFIND_ROOT):
            subprocess.check_call(['apt', 'install'])
            subprocess.check_call(['refind-install'])

        # if refind config files still can't be found after reinstall, ask user for dir
        if not os.path.exists(self.REFIND_ROOT):
            self.refind_root()

        # Todo instead of crying about this being pointless, consider adding an option to drag config file onto app or
        # add a button to load it manually that disappears on load. A warning label can appear so the user can still
        # browse as per normal but they are aware that nothing is being set because the refind file couldn't be found

        # if user provides invalid path to the refind conf, this application cannot apply skins - pointless.
        if not os.path.exists(self.REFIND_ROOT):
            exit('Unable to locate the refind configuration file!')

    def update_config(self):
        """Edits the refind.conf to apply the selected theme."""
        # with open(self.REFIND_CONFIG_FILE, 'r') as file:
        #     lines = file.readlines()
        #
        # themes_query = 'include '
        # new_theme = f"{themes_query}{self.APP_THEMES_ROOT}/{self.theme_name}/theme.conf\n"
        # print('New theme to include: ' + new_theme)
        #
        # if themes_query in lines[-1]:
        #     lines[-1] = new_theme
        # else:
        #     lines.append(new_theme)

        # if this skin has multiple backgrounds...
        if self.bg_images:
            with open(self.theme_config_file, 'r') as file:
                bg_lines = file.readlines()

            bg_query = f'banner themes/'
            bg_new = f'{bg_query}{self.theme_name}/{self.BG_FOLDER_NAME}/{self.bg_name}.png\n'

            # check if query exists in theme.conf
            for i, line in enumerate(bg_lines):
                if bg_query in line:
                    bg_lines[i] = bg_new

                    with open(self.theme_config_file, 'w') as file:
                        file.writelines(bg_lines)

        print(f"Applied theme: {self.theme_name}")

    def list_themes(self):
        """Fetches the list of themes from the themes directory."""
        if not os.path.exists(self.APP_THEMES_ROOT):
            print("Themes directory does not exist. Creating...")
            os.makedirs(self.APP_THEMES_ROOT, exist_ok=True)

        # load the path of each theme in the themes directory into a python list for easier reference
        #themes = [d for d in os.listdir(self.ROOT_THEMES_DIR)]
        themes = os.listdir(self.APP_THEMES_ROOT)

        if not themes:
            exit('No themes found in the directory.')

        print(f'Total themes found: {len(themes)}')
        return themes

    def get_sample_image_dir(self):
        """Returns the path to the theme's image or a fallback."""
        screenshot_path = os.path.join(self.SAMPLE_ROOT, f'{self.theme_name}.png')
        background_path = os.path.join(self.APP_THEMES_ROOT, 'background.png')

        # if the path leads to a folder of images
        if self.bg_images:
            return self.bg_images[self.bg_index]
        elif os.path.exists(screenshot_path):
            return screenshot_path
        elif os.path.exists(background_path):
            return background_path
        else:
            print(f'No image found for theme "{self.theme_name}", using fallback image instead.\n Path: {self.current_image_dir}')
            return self.ERROR_IMAGE  # Default image fallback

    def get_bg_images(self):
        # if the current theme has multiple backgrounds
        if os.path.isdir(self.bg_dir):
            print(f'Attempting to load background images...')
            # return a list of strings containing the directory to each background
            return [f'{self.bg_dir}/{d}' for d in os.listdir(self.bg_dir)]
        else:
            print('This image has no backgrounds, refreshing old background attributes...')
            return self.bg_refresh_attributes()

    def get_bg_name(self):
        if self.bg_images:
            match = re.search(r"(.+)/(.+)\.png", self.bg_images[self.bg_index])
            if match:
                # returns the text between the '/' and '.png' of the bg_dir
                return match.group(2)

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
        self.bg_dir = ''
        self.bg_index = 0
        self.bg_images = None

    def display_theme(self):
        # set current theme
        self.theme_name = self.themes[self.theme_index]
        self.theme_dir = os.path.join(self.APP_THEMES_ROOT, self.theme_name)
        self.theme_config_file = os.path.join(self.theme_dir, 'theme.conf')
        print(f'Local config folder located at: {self.theme_config_file}')

        self.bg_dir = os.path.join(self.SAMPLE_ROOT, self.theme_name)
        self.bg_images = self.get_bg_images()
        print(f'BG IMAGES = {self.bg_images}')
        self.bg_name = self.get_bg_name()

        # Todo simplify
        self.current_image_name = self.bg_name if self.bg_name else self.theme_name
        self.current_image_dir = self.get_sample_image_dir()

        # Show or hide up/down arrows and caption
        if self.bg_images:
            self.current_image_dir = self.bg_images[self.bg_index]
            self.image_label.config(text=f"{self.bg_index + 1}/{len(self.bg_images)}")
            self.show_bg_navigation()
        else:
            self.hide_bg_navigation()

        # Update image and write changes to config file
        self.update_image()
        self.update_config()
        self.transfer_theme_files()

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
                label = self.current_image_name.title()
                if self.bg_images:
                    label = f'{self.theme_name.title()}: ' + label
                self.theme_name_label.config(text=label)
                self.update_bg_caption()

            except Exception as e:
                print(f"Error resizing image: {e}")

    def transfer_theme_files(self):
        """
        Replaces the contents of the home_folder with the contents of the boot_folder.
        """
        # clear the existing refind theme folder
        for item in os.listdir(self.REFIND_THEME_ROOT):
            item_path = os.path.join(self.REFIND_THEME_ROOT, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            except Exception as e:
                print(f"Failed to delete {item_path}: {e}")

        print('Image dir = ' + self.theme_dir)
        # copy contents from selected theme folder to refind folder
        for item in os.listdir(self.theme_dir):
            src_path = os.path.join(self.theme_dir, item)
            dest_path = os.path.join(self.REFIND_THEME_ROOT, item)
            try:
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dest_path)
                else:
                    shutil.copy2(src_path, dest_path)
            except Exception as e:
                print(f"Failed to copy {src_path} to {dest_path}: {e}")

        print(f"Contents of '{self.REFIND_THEME_ROOT}' have been replaced with contents from '{self.theme_dir}'.")

    def next_theme(self):
        if self.themes:
            self.theme_index = (self.theme_index + 1) % len(self.themes)
            self.display_theme()

    def prev_theme(self):
        if self.themes:
            self.theme_index = (self.theme_index - 1) % len(self.themes)
            self.display_theme()

    def next_bg(self):
        if self.bg_images:
            self.bg_index = (self.bg_index + 1) % len(self.bg_images)
            self.display_theme()

    def prev_bg(self):
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
            theme_path = os.path.join(self.APP_THEMES_ROOT, theme_to_delete)
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
                messagebox.showerror("Error", f"Unable to delete theme '{theme_to_delete}': {e}")

if __name__ == "__main__":
    base_gui = tk.Tk()
    app = ThemeSelectorApp(base_gui)
    app.root.mainloop()
