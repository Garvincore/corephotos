import os
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        main = BoxLayout(orientation="vertical", spacing=10)

        header = BoxLayout(size_hint_y=None, height=dp(50))
        header.add_widget(Label(text="Family Gallery", font_size=20))

        new_post_btn = Button(text="+ Post", size_hint_x=0.3)
        new_post_btn.bind(on_press=lambda x: setattr(self.manager, "current", "post"))
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

    def on_enter(self):
        self.load_posts()

    def load_posts(self):
        self.grid.clear_widgets()

        try:
            response = requests.get(f"{BASE_URL}/data.json")
            data = response.json()
        except:
            return

        if not data or "posts" not in data:
            return

        for post in reversed(data["posts"]):

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

            self.grid.add_widget(card)


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

        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                json.dump({"posts": []}, f)

        with open(DATA_FILE, "r") as f:
            data = json.load(f)

        data["posts"].append(post)

        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

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