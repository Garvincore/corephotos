import os
import threading
import time
import json
import shutil
import requests
from datetime import datetime

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import AsyncImage
from kivy.metrics import dp
from kivy.clock import Clock


BASE_URL = "https://corephotos.web.app"
DATA_FILE = "data.json"
IMAGES_FOLDER = "images"


# ---------------- LOGIN ----------------
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation="vertical", padding=40, spacing=20)

        layout.add_widget(Label(text="Family Gallery Login", font_size=24))

        self.username = TextInput(hint_text="Enter your name", multiline=False)
        layout.add_widget(self.username)

        btn = Button(text="Enter Gallery", size_hint=(1, 0.4))
        btn.bind(on_press=self.login)
        layout.add_widget(btn)

        self.add_widget(layout)

    def login(self, instance):
        if self.username.text.strip():
            self.manager.current_user = self.username.text.strip()
            self.manager.current = "gallery"


# ---------------- GALLERY ----------------
class GalleryScreen(Screen):
    CACHE_FILE = "data_cache.json"  # local cached JSON

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.last_data = None
        self.poll_count = 0

        main = BoxLayout(orientation="vertical", spacing=10)

        header = BoxLayout(size_hint_y=None, height=dp(50))
        header.add_widget(Label(text="Family Gallery", font_size=20))

        new_post_btn = Button(text="+ Post", size_hint_x=0.3)
        new_post_btn.bind(on_press=self.on_post_button_press)
        header.add_widget(new_post_btn)

        main.add_widget(header)

        self.scroll = ScrollView()

        self.grid = GridLayout(
            cols=2,
            spacing=10,
            padding=10,
            size_hint_y=None
        )
        self.grid.bind(minimum_height=self.grid.setter("height"))

        self.scroll.add_widget(self.grid)
        main.add_widget(self.scroll)

        self.add_widget(main)

        # Load cached data if exists
        
    
    def load_cached_data(self):
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "r") as f:
                    self.last_data = json.load(f)
                    self.load_posts()
            except Exception as e:
                print("Error loading cached JSON:", e)

    def save_cache(self):
        try:
            with open(self.CACHE_FILE, "w") as f:
                json.dump(self.last_data, f)
        except Exception as e:
            print("Error saving cache:", e)

    def on_enter(self):
        # Load cached data AFTER manager exists
        self.load_cached_data()

        # Delay fetch by 1s to allow app to load first
        Clock.schedule_once(
            lambda dt: threading.Thread(
                target=self.fetch_data,
                daemon=True
            ).start(),
            1
        )

    def on_post_button_press(self, instance):
        # Open post screen
        self.manager.current = "post"

        # After posting, poll 2 times with 6s interval
        self.poll_count = 0
        Clock.schedule_interval(self.poll_after_post, 6)

    def poll_after_post(self, dt):
        if self.poll_count >= 2:
            return False  # stop scheduling
        threading.Thread(target=self.fetch_data, daemon=True).start()
        self.poll_count += 1
        return True

    def fetch_data(self):
        retries = 3
        for attempt in range(retries):
            try:
                response = requests.get(f"{BASE_URL}/data.json", timeout=10)
                data = response.json()

                if data != self.last_data:
                    self.last_data = data
                    Clock.schedule_once(lambda dt: self.load_posts())
                    self.save_cache()  # save updated data locally
                break
            except Exception as e:
                print(f"Fetch attempt {attempt+1} failed:", e)
                time.sleep(2)  # wait before retry

    def load_posts(self):
        self.grid.clear_widgets()

        if not self.last_data or "posts" not in self.last_data:
            return

        for post in reversed(self.last_data["posts"]):
            card = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(300),
                padding=5,
                spacing=5
            )

            img_url = f"{BASE_URL}/images/{post['image']}"
            card.add_widget(AsyncImage(source=img_url))

            card.add_widget(Label(
                text=f"{post['user']} - {post['category']}",
                size_hint_y=None,
                height=dp(30)
            ))

            card.add_widget(Label(
                text=post["description"],
                size_hint_y=None,
                height=dp(40)
            ))

            current_user = getattr(self.manager, "current_user", None)

            if current_user and post["user"] == current_user:
                delete_btn = Button(
                    text="Unpost",
                    size_hint_y=None,
                    height=dp(40)
                )
                delete_btn.bind(
                    on_press=lambda btn, p=post: self.unpost_photo(p)
                )
                card.add_widget(delete_btn)

            self.grid.add_widget(card)

    def unpost_photo(self, post):
        # Load current data
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
        else:
            return

        # Remove post
        data["posts"] = [p for p in data["posts"] if p != post]

        # Remove image file if exists
        image_path = os.path.join(IMAGES_FOLDER, post["image"])
        if os.path.exists(image_path):
            os.remove(image_path)

        # Save updated data
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

        # Optionally push to Git
        os.system("git add .")
        os.system('git commit -m "Removed a post"')
        os.system("git push origin main")

        # Refresh UI
        self.last_data = data
        self.load_posts()

# ---------------- POST ----------------
class PostScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        self.filechooser = FileChooserListView(
            path=os.path.expanduser("~"),
            filters=["*.png", "*.jpg", "*.jpeg"]
        )
        layout.add_widget(self.filechooser)

        self.description = TextInput(
            hint_text="Description",
            size_hint_y=None,
            height=dp(40)
        )
        layout.add_widget(self.description)

        self.category = TextInput(
            hint_text="Category (Birthday, Holiday...)",
            size_hint_y=None,
            height=dp(40)
        )
        layout.add_widget(self.category)

        post_btn = Button(text="Post Photo", size_hint_y=None, height=dp(50))
        post_btn.bind(on_press=self.create_post)
        layout.add_widget(post_btn)

        back_btn = Button(text="Back", size_hint_y=None, height=dp(40))
        back_btn.bind(on_press=lambda x: setattr(self.manager, "current", "gallery"))
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def create_post(self, instance):
        if not self.filechooser.selection:
            return

        file_path = self.filechooser.selection[0]
        filename = os.path.basename(file_path)

        # Load current posts
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"posts": []}

        # Check for duplicates
        for post in data["posts"]:
            if post["image"] == filename:
                # Found duplicate
                existing_user = post["user"]
                from kivy.uix.popup import Popup
                popup = Popup(
                    title="Duplicate Photo",
                    content=Label(
                        text=f"This photo was already posted by {existing_user}.\nDo you want to add a comment instead?"
                    ),
                    size_hint=(0.8, 0.3)
                )
                popup.open()
                return  # stop posting

        # No duplicates → continue posting
        if not os.path.exists(IMAGES_FOLDER):
            os.makedirs(IMAGES_FOLDER)

        new_path = os.path.join(IMAGES_FOLDER, filename)
        shutil.copy(file_path, new_path)

        post = {
            "user": self.manager.current_user,
            "image": filename,
            "description": self.description.text,
            "category": self.category.text,
            "timestamp": str(datetime.now())
        }

        data["posts"].append(post)

        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

        # Git push
        os.system("git add .")
        os.system('git commit -m "New family post"')
        os.system("git push origin main")

        self.manager.current = "gallery"


# ---------------- APP ----------------
class FamilyGalleryApp(App):
    def build(self):
        sm = ScreenManager()
        sm.current_user = None
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(GalleryScreen(name="gallery"))
        sm.add_widget(PostScreen(name="post"))
        return sm


if __name__ == "__main__":
    FamilyGalleryApp().run()