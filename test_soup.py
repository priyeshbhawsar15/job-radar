import asyncio
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from playwright.async_api import async_playwright

async def test_soup_parser():
    urls = [
        ('Google', 'https://www.google.com/about/careers/applications/jobs/results?location=India&q=%22Software%20Engineer%22'),
        ('Meta', 'https://www.metacareers.com/jobs?offices[0]=Bangalore%2C%20India&offices[1]=Gurgaon%2C%20India'),
        ('Walmart', 'https://walmart.wd504.myworkdayjobs.com/en-US/WalmartExternal'),
        ('Adobe', 'https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced')
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for name, url in urls:
            page = await browser.new_page(viewport={'width': 1440, 'height': 1000})
            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(2000)
                html = await page.content()

                soup = BeautifulSoup(html, 'html.parser')
                parsed_target = urlparse(url)
                print(name + ' -> Rendered ' + str(len(html)) + ' bytes')

                job_path_keywords = ['/job/', '/jobs/', '/careers/job/', 'gh_jid=', '/posting/', '/opportunities/', '/job_details/', '/job-detail/', 'R-']

                count = 0
                for a in soup.find_all('a', href=True):
                    href = a['href'].strip()
                    href_lower = href.lower()

                    is_job = any(k in href_lower for k in job_path_keywords) or bool(re.search(r'R-\d+|_R\d+|/job_details/\d+|/jobs/[0-9a-f\-]{10,}', href_lower))
                    if not is_job:
                        continue
                    if any(x in href_lower for x in ['search', 'privacy', 'terms', 'login', 'signin', 'cookie', 'gstatic', 'facebook.com', 'twitter.com']):
                        continue

                    if href.startswith('/'):
                        full_url = f"{parsed_target.scheme}://{parsed_target.netloc}{href}"
                    elif href.startswith('./'):
                        full_url = f"{parsed_target.scheme}://{parsed_target.netloc}/about/careers/applications/{href.lstrip('./')}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue

                    anchor_text = ' '.join(a.get_text(strip=True).split())
                    print('   - Title: ' + repr(anchor_text) + ' | URL: ' + full_url[:80])
                    count += 1
                    if count >= 5:
                        break
            except Exception as e:
                print(name + ' -> Error: ' + str(e))
            finally:
                await page.close()

        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_soup_parser())
