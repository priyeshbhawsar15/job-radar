import asyncio
import re
from playwright.async_api import async_playwright

async def test_playwright_inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 1000})

        url = 'https://walmart.wd504.myworkdayjobs.com/en-US/WalmartExternal?locationCountry=bc21272661f045c48b4562095f54911d'
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        html = await page.content()

        hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
        print('Total hrefs in rendered page: ' + str(len(hrefs)))

        job_hrefs = [h for h in hrefs if '/job/' in h.lower() or 'job' in h.lower() or '/walmartexternal/' in h.lower()]
        print('Job hrefs found: ' + str(len(job_hrefs)))
        for jh in job_hrefs[:10]:
            print('  - ' + jh)

        text = await page.inner_text('body')
        clean_text = ' '.join(text.split())
        print('Body text snippet: ' + clean_text[:300])

        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_playwright_inspect())
