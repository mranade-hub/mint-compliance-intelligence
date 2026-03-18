import os
import re
from playwright.sync_api import sync_playwright

BASE_URL = "https://wolfgang.tracelinkcorp.com/"
CHAT_INPUT_SELECTOR = "#chat-input"
ASSISTANT_SELECTOR = "div.chat-assistant"

BASE_DIR = os.path.dirname(__file__)
SESSION_FILE = os.path.join(BASE_DIR, "session.json")


def extract_json(text: str) -> str:
    import re
    
    # Remove markdown code fences if present
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    
    # Extract first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    
    return text.strip()  # fallback to full response


class WolfgangClient:

    def __init__(self):
        self.play = sync_playwright().start()
        self.browser, self.context, self.page = self.ensure_logged_in()

        print("✅ Wolfgang ready (persistent session)")

    # ---------------------------------

    def ensure_logged_in(self):

        # Try headless first
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

            # reopen headless
            browser = self.play.chromium.launch(headless=True)
            context = browser.new_context(storage_state=SESSION_FILE)
            page = context.new_page()
            page.goto(BASE_URL)

            page.wait_for_selector(CHAT_INPUT_SELECTOR, timeout=30000)

            return browser, context, page

    # ---------------------------------

    def upload_file(self, file_path):

        page = self.page

        print("📎 Uploading:", file_path)

        page.locator("#input-menu-button").click()

        page.locator(
            '[data-melt-dropdown-menu-item]',
            has_text="Upload Files"
        ).click()

        page.wait_for_selector("input[type=file]", state="attached")
        page.locator("input[type=file]").first.set_input_files(file_path)

        page.wait_for_timeout(4000)

        print("✅ Upload complete")

    # ---------------------------------

    def send_prompt(self, prompt: str) -> str:
        page = self.page

        # Insert prompt
        page.evaluate(
            """(text) => {
                const editor = document.querySelector("#chat-input");
                editor.innerHTML = "<p>" + text.replace(/\\n/g, "<br>") + "</p>";
                editor.dispatchEvent(new Event("input", { bubbles: true }));
            }""",
            prompt
        )

        page.keyboard.press("Enter")

        # ✅ Wait for assistant block to exist (not count increase)
        page.wait_for_selector("div.chat-assistant", timeout=180000)

        # ✅ Wait for response to stabilize
        last_text = ""
        stable_count = 0

        while stable_count < 3:
            page.wait_for_timeout(2000)
            blocks = page.locator("div.chat-assistant")
            current = blocks.nth(blocks.count() - 1).inner_text()

            if current == last_text:
                stable_count += 1
            else:
                stable_count = 0
                last_text = current

        return last_text.strip()
    
    def upload_multiple(self, file_paths):

        page = self.page

        page.wait_for_selector("#chat-input", timeout=30000)

        page.click("#input-menu-button")

        page.locator(
            '[data-melt-dropdown-menu-item]',
            has_text="Upload Files"
        ).click()

        # hidden input — DO NOT wait for visible
        file_input = page.locator("input[type=file]").first
        file_input.set_input_files(file_paths)

        page.wait_for_timeout(5000)
    # ---------------------------------

    def close(self):
        self.browser.close()
        self.play.stop()