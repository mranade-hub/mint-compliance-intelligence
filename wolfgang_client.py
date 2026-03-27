import os
import re
from playwright.sync_api import sync_playwright

BASE_URL = "https://wolfgang.tracelinkcorp.com/"
CHAT_INPUT_SELECTOR = "#chat-input"
ASSISTANT_SELECTOR = "div.chat-assistant"

BASE_DIR = os.path.dirname(__file__)
SESSION_FILE = os.path.join(BASE_DIR, "session.json")


class WolfgangClient:

    def __init__(self):
        self.play = sync_playwright().start()
        self.browser, self.context, self.page = self.ensure_logged_in()
        print("✅ Wolfgang ready (persistent session)")

    def ensure_logged_in(self):
        browser = self.play.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=SESSION_FILE if os.path.exists(SESSION_FILE) else None
        )
        page = context.new_page()
        page.goto(BASE_URL)

        try:
            page.wait_for_selector(CHAT_INPUT_SELECTOR, timeout=5000)
            return browser, context, page
        except:
            browser.close()
            print("\nSession expired. Please login...\n")
            browser = self.play.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(BASE_URL)
            page.wait_for_selector(CHAT_INPUT_SELECTOR, timeout=180000)
            context.storage_state(path=SESSION_FILE)
            print("✅ Session saved")
            browser.close()

            browser = self.play.chromium.launch(headless=True)
            context = browser.new_context(storage_state=SESSION_FILE)
            page = context.new_page()
            page.goto(BASE_URL)
            page.wait_for_selector(CHAT_INPUT_SELECTOR, timeout=30000)
            return browser, context, page

    def clear_chat(self):
        """Forces a completely new chat session to wipe the token memory clean."""
        try:
            # Navigating to the root URL forces a fresh session ID in most LLM UIs
            self.page.goto(BASE_URL, wait_until="domcontentloaded")
            self.page.wait_for_selector(CHAT_INPUT_SELECTOR, state="visible", timeout=60000)
            self.page.wait_for_timeout(3000) 
        except Exception as e:
            print(f"Failed to clear chat: {e}")

    def _force_ui_upload_menu(self):
        self.page.evaluate("""() => {
            const btn = document.querySelector("#input-menu-button");
            if(btn) btn.click();
        }""")
        self.page.wait_for_timeout(1000)
        self.page.evaluate("""() => {
            const items = Array.from(document.querySelectorAll('[data-melt-dropdown-menu-item]'));
            const upload = items.find(el => el.textContent.includes('Upload Files'));
            if(upload) upload.click();
        }""")
        self.page.wait_for_timeout(1000)

    def upload_file(self, file_path):
        page = self.page
        print("📎 Uploading:", file_path)
        page.wait_for_selector(CHAT_INPUT_SELECTOR, state="visible", timeout=60000)
        page.wait_for_timeout(2000)

        try:
            page.locator("input[type=file]").first.set_input_files(file_path, timeout=3000)
        except:
            self._force_ui_upload_menu()
            page.locator("input[type=file]").first.set_input_files(file_path)

        page.wait_for_timeout(5000)
        print("✅ Upload complete")

    def upload_multiple(self, file_paths):
        page = self.page
        page.wait_for_selector(CHAT_INPUT_SELECTOR, state="visible", timeout=60000)
        page.wait_for_timeout(2000) 

        try:
            page.locator("input[type=file]").first.set_input_files(file_paths, timeout=3000)
        except:
            self._force_ui_upload_menu()
            page.locator("input[type=file]").first.set_input_files(file_paths)
        
        page.wait_for_timeout(15000)

    def send_prompt(self, prompt: str) -> str:
        page = self.page
        page.wait_for_selector(CHAT_INPUT_SELECTOR, state="visible", timeout=120000)
        
        page.evaluate(
            """(text) => {
                const editor = document.querySelector("#chat-input");
                editor.innerHTML = "<p>" + text.replace(/\\n/g, "<br>") + "</p>";
                editor.dispatchEvent(new Event("input", { bubbles: true }));
            }""",
            prompt
        )
        
        page.wait_for_timeout(1000)
        page.keyboard.press("Enter")
        
        # Give the AI time to actually start generating before we begin checking for stability
        # This prevents premature overlaps if an error flashes on screen
        page.wait_for_timeout(5000)
        
        page.wait_for_selector("div.chat-assistant", timeout=300000)

        last_text = ""
        stable_count = 0
        
        # Increased stability requirement to 4 checks (8 seconds of no text changing) to ensure it is 100% finished
        while stable_count < 4:
            page.wait_for_timeout(2000)
            blocks = page.locator("div.chat-assistant")
            current = blocks.nth(blocks.count() - 1).inner_text()
            if current == last_text:
                stable_count += 1
            else:
                stable_count = 0
                last_text = current
                
        return last_text.strip()

    def close(self):
        self.browser.close()
        self.play.stop()