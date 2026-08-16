import asyncio
import re
from playwright.async_api import async_playwright

async def test_all_workday_playwright():
    urls = [
        ('Walmart', 'https://walmart.wd504.myworkdayjobs.com/en-US/WalmartExternal'),
        ('Adobe', 'https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced'),
        ('Cisco', 'https://cisco.wd1.myworkdayjobs.com/en-US/External_Careers'),
        ('Solera', 'https://solera.wd5.myworkdayjobs.com/en-US/Solera_Careers'),
        ('Thomson Reuters', 'https://thomsonreuters.wd5.myworkdayjobs.com/en-US/External_Careers'),
        ('TP', 'https://teleperformance.wd3.myworkdayjobs.com/en-US/TP_Careers'),
        ('eBay', 'https://ebay.wd1.myworkdayjobs.com/en-US/apply')
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for name, url in urls:
            page = await browser.new_page(viewport={'width': 1440, 'height': 1000})
            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(2000)
                html = await page.content()

                # Find job links matching /job/ or /en-US/
                hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
                job_links = [h for h in hrefs if '/job/' in h.lower() or '/details/' in h.lower() or 'R-' in h or '_R' in h]

                # Count job cards or text
                text = ' '.join((await page.inner_text('body')).split())
                print(name + ' -> Rendered ' + str(len(html)) + ' bytes, found ' + str(len(job_links)) + ' job detail links. Snippet: ' + text[:150])
            except Exception as e:
                print(name + ' -> Error: ' + str(e))
            finally:
                await page.close()

        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_all_workday_playwright())
