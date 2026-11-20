# app/auth/steam_auth.py
import asyncio
import os
import time
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright

from app.storage.steam_state import save_steam_state, find_cookie


class SteamCookieAuthManager:
    def __init__(self):
        self.profile_dir = os.getenv("STEAM_PROFILE_DIR", "/share/steam-auth/profile")
        self.state_file = os.getenv("STEAM_STATE_FILE", "/share/steam-auth/steam-state.json")
        self.language = os.getenv("LANGUAGE", "de-DE")
        self.timezone = os.getenv("TIMEZONE", "Europe/Berlin")
        self.login_timeout = int(os.getenv("STEAM_LOGIN_TIMEOUT", "300"))
        self.require_parental = os.getenv("STEAM_REQUIRE_PARENTAL", "false").lower() in (
            "1", "true", "yes", "on"
        )
        self.parental_pin = os.getenv("STEAM_PARENTAL_PIN", "").strip()

    def _find_machine_auth_cookie(self, cookies: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for cookie in cookies:
            name = cookie.get("name", "")
            if name.startswith("steamMachineAuth"):
                return cookie
        return None

    def _cookies_ready(self, cookies: List[Dict[str, Any]]) -> bool:
        steam_login = find_cookie(cookies, "steamLoginSecure", "store.steampowered.com")
        sessionid = find_cookie(cookies, "sessionid", "store.steampowered.com")

        if not steam_login or not sessionid:
            return False

        if self.require_parental:
            steam_parental = find_cookie(cookies, "steamparental", "store.steampowered.com")
            machine_auth = self._find_machine_auth_cookie(cookies)
            if not steam_parental and not machine_auth:
                return False

        return True

    async def _try_fill_first_visible(self, page, selectors: List[str], value: str) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.fill(value, timeout=1000)
                    return True
            except Exception:
                pass
        return False

    async def _try_click_first_visible(self, page, selectors: List[str]) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.click(timeout=1000)
                    return True
            except Exception:
                pass
        return False

    async def _attempt_parental_unlock(self, page) -> bool:
        if not self.parental_pin:
            return False

        open_dialog_selectors = [
            'button:has-text("Family View")',
            'button:has-text("Parental")',
            'a:has-text("Family View")',
            'a:has-text("Parental")',
            '[title*="Family View"]',
            '[aria-label*="Family View"]',
        ]

        pin_input_selectors = [
            'input[name*="pin" i]',
            'input[id*="pin" i]',
            'input[placeholder*="pin" i]',
            'input[type="password"]',
            'input[inputmode="numeric"]',
            'input[autocomplete="one-time-code"]',
            'input[maxlength="4"]',
            'input[maxlength="6"]',
        ]

        submit_selectors = [
            'button:has-text("OK")',
            'button:has-text("Ok")',
            'button:has-text("Unlock")',
            'button:has-text("Continue")',
            'button:has-text("Submit")',
            'button:has-text("Confirm")',
            'button[type="submit"]',
            'input[type="submit"]',
        ]

        await self._try_click_first_visible(page, open_dialog_selectors)
        await asyncio.sleep(0.5)

        filled = await self._try_fill_first_visible(page, pin_input_selectors, self.parental_pin)
        if not filled:
            return False

        clicked = await self._try_click_first_visible(page, submit_selectors)
        if not clicked:
            try:
                await page.keyboard.press("Enter")
            except Exception:
                pass

        await asyncio.sleep(2)
        return True

    async def login_and_export(self) -> Dict[str, Any]:
        os.makedirs(self.profile_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                self.profile_dir,
                headless=False,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
                locale=self.language,
                timezone_id=self.timezone,
                viewport={"width": 1280, "height": 900},
            )

            try:
                page = context.pages[0] if context.pages else await context.new_page()

                await page.goto("https://store.steampowered.com/", wait_until="domcontentloaded")
                await asyncio.sleep(2)

                cookies = await context.cookies()
                if self._cookies_ready(cookies):
                    save_steam_state(self.state_file, cookies)
                    return {
                        "ok": True,
                        "message": "Existing Steam profile reused",
                        "state_file": self.state_file,
                        "require_parental": self.require_parental,
                    }

                await page.goto("https://store.steampowered.com/login/", wait_until="domcontentloaded")

                deadline = time.time() + self.login_timeout
                while time.time() < deadline:
                    await asyncio.sleep(2)

                    cookies = await context.cookies()
                    if self._cookies_ready(cookies):
                        save_steam_state(self.state_file, cookies)
                        return {
                            "ok": True,
                            "message": "Steam cookies exported",
                            "state_file": self.state_file,
                            "require_parental": self.require_parental,
                        }

                    if self.require_parental and self.parental_pin:
                        await self._attempt_parental_unlock(page)
                        await asyncio.sleep(1)

                        cookies = await context.cookies()
                        if self._cookies_ready(cookies):
                            save_steam_state(self.state_file, cookies)
                            return {
                                "ok": True,
                                "message": "Steam cookies exported after parental unlock",
                                "state_file": self.state_file,
                                "require_parental": self.require_parental,
                            }

                return {
                    "ok": False,
                    "message": "Steam login timeout",
                    "state_file": self.state_file,
                    "require_parental": self.require_parental,
                }
            finally:
                await context.close()
