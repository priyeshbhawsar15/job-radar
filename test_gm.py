import asyncio
import re
from playwright.async_api import async_playwright

async def test_google_meta_rendering():
    urls = [
        ('Google', 'https://www.google.com/about/careers/applications/jobs/results?location=India&q=%22Software%20Engineer%22'),
        ('Meta', 'https://www.metacareers.com/jobs?offices[0]=Bangalore%2C%20India&offices[1]=Gurgaon%2C%20India')
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for name, url in urls:
            page = await browser.new_page(viewport={'width': 1440, 'height': 1000})
            try:
                print('Navigating to ' + name + '...')
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(3000)
                html = await page.content()

                hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
                print(name + ' -> Rendered ' + str(len(html)) + ' bytes, total hrefs: ' + str(len(hrefs)))

                job_links = [h for h in hrefs if '/jobs/' in h or 'jobs/' in h or 'v3/jobs/' in h or 'job' in h.lower()]
                print('  Job links found: ' + str(len(job_links)))
                for jl in job_links[:5]:
                    print('    - ' + jl)
            except Exception as e:
                print(name + ' -> Error: ' + str(e))
            finally:
                await page.close()

        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_google_meta_rendering())
