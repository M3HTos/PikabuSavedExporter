from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import os
import json
import time
import requests
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup


requests.packages.urllib3.disable_warnings()


class PostScrapException(Exception):
    pass


class Scrapper:
    driver = None
    cur_cat = None
    cur_post = None
    orig_name = None
    save_images = None
    save_comments = None
    options = None
    stealth = None
    init_error = False
    queue = {}

    def __init__(self, driver_type, args):
        self.create_directory(".", "saved")
        self.save_images = args.get("images", False)
        self.comments = args.get("comments", False)
        self.stealth = args.get("stealth", False)
        if driver_type != "Mozilla":
            print("Пока только лисичка. Остальные выдают ошибку, решение "
                  "которой я не могу найти :/ По крайней мере у меня краш\n"
                  "Можете проверить, закомментив self.init_error = True "
                  "в scrapper.py")
            self.init_error = True
            return
        self.set_options(driver_type)
        self.set_driver_type(driver_type)

    def set_options(self, driver):
        if driver == "Mozilla":
            from selenium.webdriver.firefox.options import Options
        elif driver == "Opera":
            from selenium.webdriver.opera.options import Options
        elif driver == "Chrome":
            from selenium.webdriver.chrome.options import Options
        self.options = Options()
        if self.stealth:
            self.options.add_argument("--headless")

    def set_driver_type(self, driver):
        if driver == "Mozilla":  # Firefox 66.0.3 (моя версия)
            self.driver = webdriver.Firefox(
                options=self.options,
                executable_path="drivers/Mozilla.exe")
        elif driver == "Opera":  # Opera 60
            self.driver = webdriver.Opera(
                options=self.options,
                executable_path="drivers/Opera.exe")
        elif driver == "Chrome":  # Chrome 74
            self.driver = webdriver.Chrome(
                options=self.options,
                executable_path="drivers/Chrome.exe")

    @staticmethod
    def create_directory(path, name):
        if not os.path.exists(f"{path}/{name}"):
            os.makedirs(f"{path}/{name}")

    @staticmethod
    def repair_name(name):
        return "".join([x if x.isalnum() else "_" for x in name])

    def start(self):
        if self.init_error:
            return
        saved = json.loads(open("saved_urls.json",  encoding="utf-8").read())
        for cat_name, cat_url in saved.items():
            if not cat_url.startswith("https"):
                cat_url = "https://" + cat_url
            cat_name = self.repair_name(cat_name)
            self.cur_cat = cat_name
            self.create_directory("saved", cat_name)
            self.queue[cat_name] = []
            self.scrap_category(cat_url)
        self.driver.quit()

    def scroll_down_category(self):
        self.driver.execute_script(
            "window.scrollTo(0, 0);")
        self.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        while True:
            time.sleep(1)
            try:
                self.driver.find_element_by_class_name("player_overlay")
            except NoSuchElementException:
                break

    def scrap_category(self, cat_url):
        self.driver.get(cat_url)
        WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((
            By.CLASS_NAME, 'main__inner')))
        while True:
            for story_div in self.driver.find_elements_by_class_name(
                    "story__main"):
                if "story__placeholder" in story_div.get_attribute("class"):
                    continue
                try:
                    story_div.find_element_by_class_name("story__sponsor")
                except NoSuchElementException:
                    pass
                else:
                    continue
                a = story_div.find_element_by_class_name(
                    "story__title-link")
                post_url = a.get_attribute("href")
                if post_url not in self.queue[self.cur_cat]:
                    self.queue[self.cur_cat].append(post_url)
            if self.driver.find_element_by_class_name(
                    "stories-feed__message").is_displayed():
                break
            else:
                self.scroll_down_category()
        self.scrap_posts()

    def scrap_posts(self):
        for category, posts in self.queue.items():
            print(f"{category} started")
            for post_url in posts:
                self.scrap_post(post_url, category)

    def scrap_post(self, post_url, category):

        def delete_element(tag, fltr):
            try:
                soup.find(tag, fltr).extract()
            except Exception:
                return

        def clear_trash():
            elems = list()
            elems.append(("header", {}))
            elems.append(("footer", {}))
            elems.append(("div", {"class": "sidebar"}))
            elems.append(("div", {"class": "page-story__similar"}))
            elems.append(("div", {"class": "page-story__cedit"}))
            elems.append(("div", {"class": "page-story__placeholder"}))
            elems.append(("div", {"class": "section-hr"}))
            elems.append(("div", {"class": "stories-feed"}))
            elems.append(("div", {"class": "page-story__comments"}))
            for element in elems:
                delete_element(*element)

        def find_video():
            for div in soup.findAll("div", {"data-type": "video"}):
                video_src = div["data-source"]
                parent = div.parent
                div.extract()
                p = soup.new_tag("p")
                p["align"] = "center"
                iframe = soup.new_tag("iframe")
                iframe["src"] = video_src
                iframe["width"] = "560"
                iframe["height"] = "315"
                iframe["frameborder"] = 0
                iframe["allow"] = "accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
                p.append(iframe)
                parent.append(p)

        def repair_gif():
            if self.save_images:
                self.create_directory(
                    f"saved/{category}/{post_name[:50]}", "gif")
            for div in soup.findAll("div", {"data-type": "gifx"}):
                gif_src = div["data-source"]
                if self.save_images:
                    gif_name = gif_src.split("/")[-1]
                    with open(f"saved/{category}/{post_name[:50]}"
                              f"/gif/{gif_name}", 'wb') as f:
                        f.write(requests.get(gif_src).content)
                    gif_src = f"gif/{gif_name}"
                parent = div.parent
                div.extract()
                p = soup.new_tag("p")
                p["align"] = "center"
                gif_img = soup.new_tag("img")
                gif_img["src"] = gif_src
                p.append(gif_img)
                parent.append(p)

        def get_images():
            if self.save_images:
                self.create_directory(
                    f"saved/{category}/{post_name[:50]}", "img")
            for div in soup.findAll("div", {"class": "story-block_type_image"}):
                img = div.find("img")
                img_src = img["src"]
                if img_src.endswith("gif"):
                    continue
                if img_src.split("?") != 1:
                    img_src = img_src.split("?")[0]
                img_name = img_src.split("/")[-1]
                r = requests.get(img_src)
                i = Image.open(BytesIO(r.content))
                if self.save_images:
                    i.save(f"saved/{category}/{post_name[:50]}/img/{img_name}")
                    img["src"] = f"img/{img_name}"
                if "data-large-image" not in img.attrs:
                    continue
                svg = div.find("svg")
                svg["height"] = i.size[1]
                if self.save_images:
                    img_src_big = img["data-large-image"]
                    img_name_big = f"big_{img_name}"
                    r = requests.get(img_src_big)
                    i = Image.open(BytesIO(r.content))
                    i.save(
                        f"saved/{category}/{post_name[:50]}/img/{img_name_big}")
                    img["data-large-image"] = f"img/{img_name_big}"

        try:
            response = requests.get(post_url, verify=False)
            soup = BeautifulSoup(response.content, "html.parser")
            orig_name = soup.find("h1", {"class": "story__title"}).text
            post_name = self.repair_name(orig_name)
            self.create_directory(f"saved/{category}", post_name[:50])
            clear_trash()
            find_video()
            repair_gif()
            get_images()
            open(f"saved/{category}/{post_name[:50]}/post.html",
                 'w', encoding="utf-16").write(soup.prettify())
            open(f"saved/{category}/{post_name[:50]}/name.txt",
                 'w', encoding="utf-8").write(orig_name)
            print(f"    {post_name} OK")
        except Exception:
            print(f"    {post_name} FAILED")
            with open("Failed posts.txt", 'a', encoding="utf-8") as file:
                file.write(post_url)
        time.sleep(1)
