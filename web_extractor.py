import os
from typing import List
import requests
from bs4 import BeautifulSoup, Comment
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import asyncio

from bing_search import BingSearch

class WebExtractor:
    def __init__(self):
        self.chrome_driver_path = os.environ.get("CHROME_DRIVER_PATH")

    def get_html_selenium(self, url):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(executable_path=self.chrome_driver_path, options=chrome_options)

        driver.set_page_load_timeout(5)
        driver.implicitly_wait(5)

        try:
            driver.get(url)
        except:
            print(f"Error fetching {url}")
            driver.quit()
            return ''

        # Get the HTML content
        html_content = driver.page_source
        driver.quit()

        return html_content

    def get_html_requests(self, url):
        response = requests.get(url)
        return response.text

    def tag_visible(self, element):
        if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
            return False
        if isinstance(element, Comment):
            return False
        return True

    def default_tokenizer(text):
        return list(text)

    def text_from_html(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        texts = soup.findAll(text=True)
        visible_texts = filter(self.tag_visible, texts)
        return " ".join(t.strip() for t in visible_texts)

    def driver_available(self):
        return self.chrome_driver_path is not None

    async def extract_text(self, url, tokenizer=default_tokenizer, tokens_per_chunk=2000) -> List[str]:
        if not self.driver_available():
            raise Exception("Chrome WebDriver path not found. Set CHROME_DRIVER_PATH environment variable.")
        loop = asyncio.get_event_loop()
        html = await loop.run_in_executor(None, self.get_html_requests, url)
        visible_text = await loop.run_in_executor(None, self.text_from_html, html)

        tokens = tokenizer(visible_text)
        chunks = [''.join(tokens[i:i + tokens_per_chunk]) for i in range(0, len(tokens), tokens_per_chunk)]
        return chunks



