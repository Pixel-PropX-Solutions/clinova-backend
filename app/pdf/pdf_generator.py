import asyncio
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright

_executor = ThreadPoolExecutor(max_workers=2)


def _generate_pdf_sync(html_content: str) -> bytes:
    """
    Synchronous PDF generation using Playwright Chromium.
    Runs in a thread to avoid Windows asyncio subprocess issues.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")

        pdf_bytes = page.pdf(
            print_background=True,
            format="A4",
            margin={"top": "1cm", "right": "1cm", "bottom": "1cm", "left": "1cm"}
        )

        browser.close()
        return pdf_bytes


async def generate_pdf(html_content: str) -> bytes:
    """
    Async wrapper — offloads Playwright to a thread so it works on Windows.
    """
    loop = asyncio.get_event_loop()
    pdf_bytes = await loop.run_in_executor(_executor, _generate_pdf_sync, html_content)
    return pdf_bytes
