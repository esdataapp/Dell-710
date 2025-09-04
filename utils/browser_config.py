import sys
from typing import List


def get_chromium_args() -> List[str]:
    """Return a list of Chromium args depending on the platform.

    Ensures headless mode works across Linux and Windows 11 terminals.
    """
    if sys.platform.startswith("win"):
        return [
            "--disable-gpu",
            "--disable-extensions",
            "--disable-sync",
            "--disable-translate",
            "--hide-scrollbars",
            "--mute-audio",
            "--no-first-run",
            "--safebrowsing-disable-auto-update",
            "--ignore-ssl-errors",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--window-size=1920,1080",
        ]

    return [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-sync",
        "--disable-translate",
        "--hide-scrollbars",
        "--mute-audio",
        "--no-first-run",
        "--safebrowsing-disable-auto-update",
        "--ignore-ssl-errors",
        "--ignore-certificate-errors",
        "--allow-running-insecure-content",
        "--disable-web-security",
        "--disable-features=VizDisplayCompositor",
    ]
