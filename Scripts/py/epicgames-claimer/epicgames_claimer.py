import argparse
import asyncio
import json
import os
import signal
import time
from getpass import getpass
from json.decoder import JSONDecodeError
from typing import Dict, List, Optional, Union

import schedule
from pyppeteer import launch, launcher
from pyppeteer.element_handle import ElementHandle
from pyppeteer.network_manager import Request


class epicgames_claimer:
    def __init__(self, data_dir: Optional[str] = None, headless: bool = True, sandbox: bool = False, chromium_path: Optional[str] = None) -> None:
        if "--enable-automation" in launcher.DEFAULT_ARGS:
            launcher.DEFAULT_ARGS.remove("--enable-automation")
        # Solve the problem of zombie processes
        if "SIGCHLD" in dir(signal):
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        self.data_dir = data_dir
        self.headless = headless
        self.sandbox = sandbox
        self.chromium_path = chromium_path
        self._loop = asyncio.get_event_loop()
        self.browser_opened = False
        self.page = None
        self.open_browser()
    
    @staticmethod
    def log(text: str, level: str = "info") -> None:
        localtime = time.asctime(time.localtime(time.time()))
        if level == "info":
            print("[{}] {}".format(localtime, text))
        elif level == "warning":
            print("\033[33m[{}] Warning: {}\033[0m".format(localtime, text))
        elif level == "error":
            print("\033[31m[{}] Error: {}\033[0m".format(localtime, text))

    async def _headless_stealth_async(self):
        await self.page.evaluateOnNewDocument(
            "() => {"
                "Object.defineProperty(navigator, 'appVersion', {get: () => '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3542.0 Safari/537.36',});"
                "Object.defineProperty(navigator, 'plugins', {get: () => [{'description': 'Portable Document Format', 'filename': 'internal-pdf-viewer', 'length': 1, 'name': 'Chrome PDF Plugin'}]});"
                "Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en'],});"
                "const originalQuery = window.navigator.permissions.query;"
                "window.navigator.permissions.query = (parameters) => (parameters.name === 'notifications' ? Promise.resolve({ state: Notification.permission }) : originalQuery(parameters));"
                "window.chrome = {}; window.chrome.app = {'InstallState':'a', 'RunningState':'b', 'getDetails':'c', 'getIsInstalled':'d'}; window.chrome.csi = function(){}; window.chrome.loadTimes = function(){}; window.chrome.runtime = function(){};"
                "const newProto = navigator.__proto__; delete newProto.webdriver; navigator.__proto__ = newProto;"
                "Reflect.defineProperty(navigator.connection,'rtt', {get: () => 150, enumerable:true});"
                "const getParameter = WebGLRenderingContext.getParameter; WebGLRenderingContext.prototype.getParameter = function(parameter) {if (parameter === 37445) {return 'Intel Open Source Technology Center';}; if (parameter === 37446) {return 'Mesa DRI Intel(R) Ivybridge Mobile ';}; return getParameter(parameter);};"
                "['height', 'width'].forEach(property => {const imageDescriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, property); Object.defineProperty(HTMLImageElement.prototype, property, {...imageDescriptor, get: function() {if (this.complete && this.naturalHeight == 0) {return 16;}; return imageDescriptor.get.apply(this);},});});"
            "}"
        )
        await self.page.evaluateOnNewDocument("window.navigator.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}, app: {}};")
        await self.page.evaluateOnNewDocument("window.navigator.language = {runtime: {}, loadTimes: function() {}, csi: function() {}, app: {}};")
        await self.page.setExtraHTTPHeaders({"Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"})
        await self.page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3542.0 Safari/537.36")

    async def _open_browser_async(self) -> None:
        if not self.browser_opened:
            if "win" in launcher.current_platform():
                if self.chromium_path == None and os.path.exists("chrome-win32"):
                    self.chromium_path = "chrome-win32/chrome.exe"
            browser_args = [
                "--disable-infobars",
                "--blink-settings=imagesEnabled=false",
                "--no-first-run"
            ]
            if not self.sandbox:
                browser_args.append("--no-sandbox")
            self.browser = await launch(
                options={"args": browser_args, "headless": self.headless}, 
                userDataDir=None if self.data_dir == None else os.path.abspath(self.data_dir), 
                executablePath=self.chromium_path,
            )
            self.page = (await self.browser.pages())[0]
            await self.page.setViewport({"width": 1000, "height": 600})
            # Async callback functions aren't possible to use(Refer to https://github.com/pyppeteer/pyppeteer/issues/220).
            # await self.page.setRequestInterception(True)
            # self.page.on('request', self._intercept_request_async)
            if self.headless:
                await self._headless_stealth_async()
            self.browser_opened = True

    async def _intercept_request_async(self, request: Request) -> None:
        if request.resourceType in ["image", "media", "font"]:
            await request.abort()
        else:
            await request.continue_()
        
    async def _close_browser_async(self):
        if self.browser_opened:
            await self.browser.close()
            self.browser_opened = False
    
    async def _type_async(self, selector: str, text: str, sleep: Union[int, float] = 0) -> None:
        await self.page.waitForSelector(selector)
        await asyncio.sleep(sleep)
        await self.page.type(selector, text)

    async def _click_async(self, selector: str, sleep: Union[int, float] = 2, timeout: int = 30000, frame_index: int = 0) -> None:
        if frame_index == 0:
            await self.page.waitForSelector(selector, options={"timeout": timeout})
            await asyncio.sleep(sleep)
            await self.page.click(selector)
        else:
            await self.page.waitForSelector("iframe:nth-child({})".format(frame_index), options={"timeout": timeout})
            frame = self.page.frames[frame_index]
            await frame.waitForSelector(selector)
            await asyncio.sleep(sleep)
            await frame.click(selector)

    async def _get_text_async(self, selector: str) -> str:
        await self.page.waitForSelector(selector)
        return await (await (await self.page.querySelector(selector)).getProperty("textContent")).jsonValue()

    async def _get_texts_async(self, selector: str) -> List[str]:
        texts = []
        try:
            await self.page.waitForSelector(selector)
            for element in await self.page.querySelectorAll(selector):
                texts.append(await (await element.getProperty("textContent")).jsonValue())
        except:
            pass
        return texts

    async def _get_element_text_async(self, element: ElementHandle) -> str:
        return await (await element.getProperty("textContent")).jsonValue()

    async def _get_property_async(self, selector: str, property: str) -> str:
        await self.page.waitForSelector(selector)
        return await self.page.evaluate("document.querySelector('{}').getAttribute('{}')".format(selector, property))

    async def _get_links_async(self, selector: str, filter_selector: str, filter_value: str) -> List[str]:
        links = []
        try:
            await self.page.waitForSelector(selector)
            elements = await self.page.querySelectorAll(selector)
            judgement_texts = await self._get_texts_async(filter_selector)
        except:
            return []
        for element, judgement_text in zip(elements, judgement_texts):
            if judgement_text == filter_value:
                link = await (await element.getProperty("href")).jsonValue()
                links.append(link)
        return links

    async def _find_async(self, selectors: Union[str, List[str]], timeout: int = None) -> Union[bool, int]:
        if type(selectors) == str:
            try:
                if timeout == None:
                    timeout = 1000
                await self.page.waitForSelector(selectors, options={"timeout": timeout})
                return True
            except:
                return False
        elif type(selectors) == list:
            if timeout == None:
                timeout = 300000
            for _ in range(int(timeout / 1000 / len(selectors))):
                for i in range(len(selectors)):
                    if await self._find_async(selectors[i], timeout=1000):
                        return i
            return -1
        else:
            raise ValueError
    
    async def _find_and_not_find_async(self, find_selector: str, not_find_selector: str, timeout: int = 60000) -> int:
        for _ in range(int(timeout / 1000 / 2)):
            if await self._find_async(find_selector, timeout=1000):
                return 0
            elif not await self._find_async(not_find_selector, timeout=1000):
                return 1
        return -1

    async def _try_click_async(self, selector: str, sleep: Union[int, float] = 2) -> bool:
        try:
            await asyncio.sleep(sleep)
            await self.page.click(selector)
            return True
        except:
            return False

    async def _get_elements_async(self, selector: str) -> Union[List[ElementHandle], None]:
        try:
            await self.page.waitForSelector(selector)
            return await self.page.querySelectorAll(selector)
        except:
            return None

    async def _wait_for_element_text_change_async(self, element: ElementHandle, text: str, timeout: int = 30) -> None:
        if await self._get_element_text_async(element) != text:
            return
        for _ in range(timeout):
            await asyncio.sleep(1)
            if await self._get_element_text_async(element) != text:
                return
        raise TimeoutError("Waiting for element \"{}\" text content change failed: timeout {}s exceeds".format(element, timeout))

    async def _navigate_async(self, url: str, timeout: int = 30000, reload: bool = True) -> None:
        if self.page.url == url and not reload:
            return
        await self.page.goto(url, options={"timeout": timeout})

    async def _close_autoplay_async(self):
        await self._navigate_async("https://www.epicgames.com/store/en-US/p/fortnite")
        await self._click_async("button[data-testid=settings-button]")
        if await self._find_async("#on[checked]", timeout=4000):
            await self._click_async("div[data-testid=settings-container] button")
            await asyncio.sleep(2)
    
    async def _get_url_json_async(self, url: str) -> Dict:
        response_text = await self._get_async(url)
        try:
            response_json = json.loads(response_text)
        except JSONDecodeError:
            response_text_partial = response_text if len(response_text) <= 96 else response_text[0:96]
            raise ValueError("Epic Games returnes content that cannot be resolved. Response: {} ...".format(response_text_partial))
        return response_json

    async def _login_async(self, email: str, password: str, tfa_enabled: bool = True, remember_me: bool = True) -> None:
        if email == None or email == "":
            raise ValueError("Email can't be null.")
        if password == None or password == "":
            raise ValueError("Password can't be null.")
        if await self._need_login_async():
            await self._navigate_async("https://www.epicgames.com/store/en-US/", timeout=120000, reload=False)
            await self._click_async("#user", timeout=120000)
            await self._click_async("#login-with-epic", timeout=120000)
            await self._type_async("#email", email)
            await self._type_async("#password", password)
            if not remember_me:
                await self._click_async("#rememberMe")
            await self._click_async("#sign-in[tabindex='0']", timeout=120000)
            login_result = await self._find_async(["#talon_frame_login_prod[style*=visible]", "div.MuiPaper-root[role=alert] h6[class*=subtitle1]", "#modal-content", "#user"], timeout=60000)
            if login_result == 0:
                raise PermissionError("CAPTCHA is required for unknown reasons.")
            elif login_result == 1:
                alert_text = await self._get_text_async("div.MuiPaper-root[role=alert] h6[class*=subtitle1]")
                raise PermissionError("From Epic Games: {}".format(alert_text))
            elif login_result == 2: 
                if tfa_enabled:
                    await self._type_async("input[name=code-input-0]", input("Verification code: "))
                    await self._click_async("#continue[tabindex='0']", timeout=120000)
                    await self.page.waitForSelector("#user")
                else:
                    raise ValueError("Verification code is required. You need to turn off two-factor authentication of this account.")

    async def _login_no_check_async(self, email: str, password: str, tfa_enabled: bool = True, remember_me: bool = True) -> None:
        if email == None or email == "":
            raise ValueError("Email can't be null.")
        if password == None or password == "":
            raise ValueError("Password can't be null.")
        await self._navigate_async("https://www.epicgames.com/store/en-US/", timeout=120000, reload=False)
        await self._click_async("#user", timeout=120000)
        await self._click_async("#login-with-epic", timeout=120000)
        await self._type_async("#email", email)
        await self._type_async("#password", password)
        if not remember_me:
            await self._click_async("#rememberMe")
        await self._click_async("#sign-in[tabindex='0']", timeout=120000)
        login_result = await self._find_async(["#talon_frame_login_prod[style*=visible]", "div.MuiPaper-root[role=alert] h6[class*=subtitle1]", "input[name=code-input-0]", "#user"], timeout=90000)
        if login_result == 0:
            raise PermissionError("CAPTCHA is required for unknown reasons.")
        elif login_result == 1:
            alert_text = await self._get_text_async("div.MuiPaper-root[role=alert] h6[class*=subtitle1]")
            raise PermissionError("From Epic Games: {}".format(alert_text))
        elif login_result == 2: 
            if tfa_enabled:
                await self._type_async("input[name=code-input-0]", input("Verification code: "))
                await self._click_async("#continue[tabindex='0']", timeout=120000)
                await self.page.waitForSelector("#user")
            else:
                raise ValueError("Verification code is required. You need to turn off two-factor authentication of this account.")

    async def _need_login_async(self, use_web_api: bool = False) -> bool:
        if use_web_api:
            page_content_json = await self._get_url_json_async("https://www.epicgames.com/account/v2/ajaxCheckLogin")
            return page_content_json["needLogin"]
        else:
            await self._navigate_async("https://www.epicgames.com/store/en-US/", timeout=120000)
            if (await self._get_property_async("#user", "data-component")) == "SignedIn":
                return False
            else:
                return True

    async def _get_free_game_links_async(self) -> List[str]:
        page_content_json = await self._get_url_json_async("https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions")
        free_games = page_content_json["data"]["Catalog"]["searchStore"]["elements"]
        free_game_links = []
        for free_game in free_games:
            if {"path": "freegames"} in free_game["categories"]:
                if free_game["price"]["totalPrice"]["discount"] != 0:
                    free_game_links.append("https://www.epicgames.com/store/p/{}".format(free_game["productSlug"]))
        return free_game_links
       
    async def _claim_async(self) -> List[str]:
        free_games = await self._get_free_game_infos_async()
        claimed_game_titles = []
        alert_text_list = []
        claim_failed = False
        check_claim_result_failed = []
        for game in free_games:
            await self._navigate_async(game["purchase_url"], timeout=60000)
            await self._click_async("#purchase-app button[class*=confirm]:not([disabled])", timeout=60000)
            claim_result = await self._find_and_not_find_async("#purchase-app div[class*=alert]", "#purchase-app > div", timeout=120000)
            if claim_result == 0:
                alert_text = await self._get_text_async("#purchase-app div[class*=alert]:not([disabled])")
                if not "already own this item" in alert_text:
                    claim_failed = True
                    alert_text_list.append(alert_text)
            elif claim_result == 1:
                claimed_game_titles.append(game["title"])
            elif claim_result == -1:
                check_claim_result_failed.append(game["title"])
        if claim_failed:
            raise PermissionError("From Epic Games: {}".format(str(alert_text_list).strip("[]").replace("'", "").replace(",", "")))
        elif len(check_claim_result_failed) != 0:
            raise TimeoutError("Check claim result failed: {}.".format(str(check_claim_result_failed).strip("[]").replace("'", "")))
        else:
            return claimed_game_titles
    
    async def _get_authentication_method_async(self) -> Optional[str]:
        page_content_json = await self._get_url_json_async("https://www.epicgames.com/account/v2/security/settings/ajaxGet")
        if page_content_json["settings"]["enabled"] == False:
            return None
        else:
            return page_content_json["settings"]["defaultMethod"]
    
    def _quit(self, signum = None, frame = None) -> None:
        try:
            self.close_browser()
        except:
            pass
        exit(1)

    def open_browser(self) -> None:
        """Open the browser."""
        return self._loop.run_until_complete(self._open_browser_async())

    def close_browser(self) -> None:
        """Close the browser."""
        return self._loop.run_until_complete(self._close_browser_async())
    
    def need_login(self) -> bool:
        """Return whether need login."""
        return self._loop.run_until_complete(self._need_login_async())
    
    def login(self, email: str, password: str, two_fa_enabled: bool = True, remember_me: bool = True) -> None:
        """Login an Epic account."""
        return self._loop.run_until_complete(self._login_async(email, password, two_fa_enabled, remember_me))\
    
    def get_authentication_method(self) -> Optional[str]:
        """Return authentication method. sms, authenticator, email or None."""
        return self._loop.run_until_complete(self._get_authentication_method_async())
    
    def get_free_game_links(self) -> List[str]:
        """Return all titles of weekly free games."""
        return self._loop.run_until_complete(self._get_free_game_links_async())

    def claim(self) -> List[str]:
        """Claim available weekly free games and return all titles of claimed games."""
        return self._loop.run_until_complete(self._claim_async())
    
    async def _screenshot_async(self, path: str) -> None:
        await self.page.screenshot({"path": path})

    def screenshot(self, path: str) -> None:
        return self._loop.run_until_complete(self.page.screenshot({"path": path}))    
    
    def navigate(self, url: str, timeout: int = 30000, reload: bool = True) -> None:
        return self._loop.run_until_complete(self._navigate_async(url, timeout, reload))


    def logged_login(self, retries: int = 5) -> bool:
        """Login method Contains retry and log output."""
        for _ in range(retries):
            try:
                if self.need_login():
                    self.log("Need login.")
                    self.close_browser()
                    email = input("Email: ")
                    password = getpass("Password: ")
                    self.open_browser()
                    self.login(email, password)
                    self.log("Login successed.")
                return True
            except Exception as e:
                self.log("Login failed({}).".format(e), "warning")
        self.log("Login failed.", "error")
        self.screenshot("screenshot.png")
        return False

    def logged_login_no_interactive(self, email: str, password: str, retries: int = 3) -> bool:
        """Login method Contains retry and log output."""
        for _ in range(retries):
            try:
                if self.need_login():
                    self.login(email, password, two_fa_enabled=False)
                    self.log("Login successed.")
                return True
            except Exception as e:
                self.log("Login failed({}).".format(e), "warning")
        self.log("Login failed.", "error")
        self.screenshot("screenshot.png")
        return False
    
    def logged_claim(self, retries: int = 5) -> None:
        """Claim method Contains retry and log output."""
        for _ in range(0, retries):
            try:
                claimed_game_titles = self.claim()
                if len(claimed_game_titles) > 0:
                    self.log("{} has been claimed.".format(str(claimed_game_titles).strip("[]").replace("'", "")))
                return
            except Exception as e:
                self.log("{}.".format(str(e).rstrip(".")), level="warning")
        self.log("Claim failed.", level="error")
        self.screenshot("screenshot.png")


    def run(self, at: str = None, once: bool = False) -> None:
        """Claim all weekly free games everyday."""
        signal.signal(signal.SIGINT, self._quit)
        signal.signal(signal.SIGTERM, self._quit)
        if "SIGBREAK" in dir(signal):
            signal.signal(signal.SIGBREAK, self._quit)
        if "SIGHUP" in dir(signal):
            signal.signal(signal.SIGHUP, self._quit)
        def everyday_job() -> None:
            self.open_browser()
            self.logged_claim()
            self.close_browser()
        self.logged_claim()
        self.close_browser()
        if at == None or once:
            return
        schedule.every().day.at(at).do(everyday_job)
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    async def _post_json_async(self, url: str, data: str, host: str = "www.epicgames.com", sleep: Union[int, float] = 2):
        await asyncio.sleep(sleep)
        if not host in self.page.url:
            await self._navigate_async("https://{}".format(host))
        response = await self.page.evaluate("""
            xmlhttp = new XMLHttpRequest();
            xmlhttp.open("POST", "{}", true);
            xmlhttp.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
            xmlhttp.send('{}');
            xmlhttp.responseText;
        """.format(url, data))
        return response
    
    def post_json(self, url: str, data: str, host: str = "www.epicgames.com", sleep: Union[int, float] = 2):
        return self._loop.run_until_complete(self._post_json_async(url, data, host, sleep))
    
    async def _get_account_id_async(self):
        if await self._need_login_async():
            return None
        else:
            await self._navigate_async("https://www.epicgames.com/account/personal")
            account_id =  (await self._get_text_async("#personalView div.paragraph-container p")).split(": ")[1]
            return account_id

    def get_account_id(self):
        return self._loop.run_until_complete(self._get_account_id_async())
    
    async def _get_async(self, url: str, sleep: Union[int, float] = 3):
        await self._navigate_async(url)
        response_text = await self._get_text_async("body")
        await asyncio.sleep(sleep)
        return response_text

    def get(self, url: str, sleep: Union[int, float] = 2):
        return self._loop.run_until_complete(self._get_async(url, sleep))
    
    async def _get_game_infos_async(self, url_slug: str):
        game_infos = {}
        response_text = await self._get_async("https://store-content.ak.epicgames.com/api/zh-CN/content/products/{}".format(url_slug))
        response_json = json.loads(response_text)
        game_infos["product_name"] = response_json["productName"]
        game_infos["namespace"] = response_json["namespace"]
        game_infos["pages"] = []
        for page in response_json["pages"]:
            game_info_page = {}
            if page["offer"]["hasOffer"]:
                game_info_page["offer_id"] = page["offer"]["id"]
                game_info_page["namespace"] = page["offer"]["namespace"]
                game_infos["pages"].append(game_info_page)
        return game_infos
    
    def get_game_infos(self, url_slug: str):
        return self._loop.run_until_complete(self._get_game_infos_async(url_slug))
    
    async def _get_order_sync_token_async(self, namespace:str, order_id: str):
        post_text = """
            {{
                "useDefault":true,
                "setDefault":false,
                "orderId":null,
                "namespace":"{}",
                "country":null,
                "countryName":null,
                "orderComplete":null,
                "orderError":null,
                "orderPending":null,
                "offers":["{}"],
                "offerPrice":""
            }}""".format(namespace, order_id)
        post_text = post_text.replace(" ", "")
        post_text = post_text.replace("\n", "")
        response_text = await self._post_json_async("/purchase/order-preview", post_text, "payment-website-pci.ol.epicgames.com")
        response_json = json.loads(response_text)
        sync_token = response_json["syncToken"]
        return sync_token
    
    def get_order_sync_token(self, namespace:str, offer_id: str):
        return self._loop.run_until_complete(self._get_order_sync_token_async(namespace, offer_id))
    
    def get_purchase_url(self, namespace:str, offer_id: str):
        purchase_url = "https://www.epicgames.com/store/purchase?lang=en-US&namespace={}&offers={}".format(namespace, offer_id)
        return purchase_url
    
    async def _get_library_items_async(self):
        post_text = """
            {
                "query":"
                    query libraryQuery($cursor: String, $excludeNs: [String]) {
                        Library {
                            libraryItems(cursor: $cursor, params: {excludeNs: $excludeNs, includeMetadata: true}) {
                                records {
                                    catalogItemId
                                    namespace
                                    appName
                                    productId
                                    product {
                                        supportedTypes
                                    }
                                }
                                responseMetadata {
                                    nextCursor
                                }
                            }
                        }
                    }
                    ",
                "variables":{
                    "cursor":"",
                    "excludeNs":["ue"]
                }
            }
        """
        post_text = post_text.replace(" ", "")
        post_text = post_text.replace("\n", "")
        response_text = await self._post_json_async("https://store-launcher.epicgames.com/graphql", post_text, "store-launcher.epicgames.com")
        response_json = json.loads(response_text)
        library_items = response_json["data"]["Library"]["libraryItems"]["records"]
        return library_items
    
    def get_library_items(self):
        return self._loop.run_until_complete(self._get_library_items_async())
    
    async def _get_free_game_infos_async(self) -> List[Dict[str, str]]:
        response_text = await self._get_async("https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions")
        response_json = json.loads(response_text)
        free_game_infos = []
        for item in response_json["data"]["Catalog"]["searchStore"]["elements"]:
            free_game_info = {}
            if {"path": "freegames"} in item["categories"]:
                if item["price"]["totalPrice"]["discountPrice"] == 0 and item["price"]["totalPrice"]["originalPrice"] != 0:
                    free_game_info["title"] = item["title"]
                    free_game_info["url_slug"] = item["urlSlug"]
                    free_game_info["namespace"] = item["namespace"]
                    free_game_info["offer_id"] = item["id"]
                    free_game_info["url"] = "https://www.epicgames.com/store/p/" + free_game_info["url_slug"]
                    free_game_info["purchase_url"] = "https://www.epicgames.com/store/purchase?lang=en-US&namespace={}&offers={}".format(free_game_info["namespace"], free_game_info["offer_id"])
                    free_game_infos.append(free_game_info)
        return free_game_infos
    
    def get_free_game_infos(self) -> List[Dict[str, str]]:
        return self._loop.run_until_complete(self._get_free_game_infos_async())
    
    async def _is_in_library_async(self, account_id: str, namespace: str, sha256_hash: str):
        # sha256_hash need to be decoded.
        response_text = await self._get_async("https://www.epicgames.com/graphql?operationName=getAccountEntitlements&variables=%7B%22accountId%22:%22{}%22,%22namespace%22:%22{}%22%7D&extensions=%7B%22persistedQuery%22:%7B%22version%22:1,%22sha256Hash%22:%22{}%22%7D%7D".format(account_id, namespace, sha256_hash))
        response_json = json.loads(response_text)
        in_library = True if response_json["data"]["Entitlements"]["accountEntitlements"]["count"] > 0 else False
        return in_library

    async def _run_async(self, retries: int = 5) -> None:
        await self._open_browser_async()
        for i in range(retries):
            try:
                if await self._need_login_async():
                    self.log("Need login.")
                    await self._close_browser_async()
                    email = input("Email: ")
                    password = getpass("Password: ")
                    await self._open_browser_async()
                    await self._login_no_check_async(email, password)
                    self.log("Login successed.")
                break
            except Exception as e:
                self.log("{}".format(e), level="warning")
                if i == retries - 1:
                    self.log("Login failed.", "error")
                    await self._screenshot_async("screenshot.png")
                    await self._close_browser_async()
                    exit(1)
        for i in range(retries):
            try:
                claimed_game_titles = await self._claim_async()
                if len(claimed_game_titles) > 0:
                    self.log("{} has been claimed.".format(str(claimed_game_titles).strip("[]").replace("'", "")))
                else:
                    self.log("All available weekly free games are already in your library.")
                break
            except Exception as e:
                self.log("{}".format(e), level="warning")
                if i == retries - 1:
                    self.log("Claim failed.", level="error")
                    await self._screenshot_async("screenshot.png")
        await self._close_browser_async()
    
    async def _run_no_interactive_async(self, email: str, password: str, retries: int = 5) -> None:
        await self._open_browser_async()
        for i in range(retries):
            try:
                if await self._need_login_async():
                    await self._login_no_check_async(email, password, tfa_enabled=False, remember_me=False)
                break
            except Exception as e:
                self.log("{}".format(e), level="warning")
                if i == retries - 1:
                    self.log("Login failed.", "error")
                    await self._screenshot_async("screenshot.png")
                    await self._close_browser_async()
                    exit(1)
        for i in range(retries):
            try:
                claimed_game_titles = await self._claim_async()
                if len(claimed_game_titles) > 0:
                    self.log("{} has been claimed.".format(str(claimed_game_titles).strip("[]").replace("'", "")))
                else:
                    self.log("All available weekly free games are already in your library.")
                break
            except Exception as e:
                self.log("{}".format(e), level="warning")
                if i == retries - 1:
                    self.log("Claim failed.", level="error")
                    await self._screenshot_async("screenshot.png")
        await self._close_browser_async()
    
    def run_once(self, interactive: bool = True, email: str = None, password: str = None) -> None:
        if interactive:
            return self._loop.run_until_complete(self._run_async(retries=5))
        else:
            return self._loop.run_until_complete(self._run_no_interactive_async(email, password, retries=5))
    
    def scheduled_run(self, at: str, interactive: bool = True, email: str = None, password: str = None) -> None:
        self.add_quit_signal()
        schedule.every().day.at(at).do(self.run_once, interactive, email, password)
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def add_quit_signal(self):
        signal.signal(signal.SIGINT, self._quit)
        signal.signal(signal.SIGTERM, self._quit)
        if "SIGBREAK" in dir(signal):
            signal.signal(signal.SIGBREAK, self._quit)
        if "SIGHUP" in dir(signal):
            signal.signal(signal.SIGHUP, self._quit)

def get_args(include_auto_update: bool = False) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Claim weekly free games from Epic Games Store.")
    parser.add_argument("-n", "--no-headless", action="store_true", help="run the browser with GUI")
    parser.add_argument("-c", "--chromium-path", type=str, help="set path to browser executable")
    parser.add_argument("-r", "--run-at", type=str, help="set daily check and claim time(HH:MM)")
    parser.add_argument("-o", "--once", action="store_true", help="claim once then exit")
    if include_auto_update:
        parser.add_argument("-a", "--auto-update", action="store_true", help="enable auto update")
    parser.add_argument("-u", "--username", type=str, help="set username/email")
    parser.add_argument("-p", "--password", type=str, help="set password")
    args = parser.parse_args()
    if args.run_at == None:
        localtime = time.localtime()
        args.run_at = "{0:02d}:{1:02d}".format(localtime.tm_hour, localtime.tm_min)
    env_run_at = os.environ.get("RUN_AT")
    env_once = os.environ.get("ONCE")
    if include_auto_update:
        env_auto_update = os.environ.get("AUTO_UPDATE")
    env_email = os.environ.get("EMAIL")
    env_password = os.environ.get("PASSWORD")
    if env_run_at != None:
        args.run_at = env_run_at
    if env_once == "true":
        args.once = True
    elif env_once == "false":
        args.once = False
    if include_auto_update:
        if env_auto_update == "true":
            args.auto_update = True
        elif env_auto_update == "false":
            args.auto_update = False
    if env_email != None:
        args.username = env_email
    if env_password != None:
        args.password = env_password
    if args.username != None and args.password == None:
        raise ValueError("Must input both username and password.")
    if args.username == None and args.password != None:
        raise ValueError("Must input both username and password.")
    return args

def main() -> None:
    args = get_args()
    if args.username != None:
        if args.password == None:
            raise ValueError("Must input both username and password.")
    interactive = True if args.username == None else False
    data_dir = "User_Data/Default" if interactive else None
    epicgames_claimer.log("Claimer is starting...")
    claimer = epicgames_claimer(data_dir, headless=not args.no_headless, chromium_path=args.chromium_path)
    if args.once == True:
        epicgames_claimer.log("Claimer started.")
        claimer.run_once(interactive, args.username, args.password)
        epicgames_claimer.log("Claim completed.")
    else:
        epicgames_claimer.log("Claimer started. Run at {} everyday.".format(args.run_at))
        claimer.run_once(interactive, args.username, args.password)
        claimer.scheduled_run(args.run_at, interactive, args.username, args.password)


if __name__ == "__main__":
    main()
