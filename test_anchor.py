import asyncio
import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright

async def test_anchor_parser():
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

                parsed_target = urlparse(url)
                print(name + ' -> Rendered ' + str(len(html)) + ' bytes')

                job_path_keywords = ['/job/', '/jobs/', '/careers/job/', 'gh_jid=', '/posting/', '/opportunities/', '/job_details/', '/job-detail/', 'R-']

                matches = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)

                count = 0
                seen = set()
                for href, inner in matches:
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

                    clean_url = full_url.split('?')[0] if '?' in full_url and not any(k in full_url for k in ['gh_jid=', 'jobId=']) else full_url

                    if clean_url in seen or clean_url.rstrip('/') == url.rstrip('/'):
                        continue
                    seen.add(clean_url)

                    clean_text = re.sub(r'<[^>]+>', ' ', inner).strip()
                    clean_text = ' '.join(clean_text.split())

                    print('   - Title: ' + repr(clean_text) + ' | URL: ' + clean_url[:80])
                    count += 1
                    if count >= 5:
                        break
            except Exception as e:
                print(name + ' -> Error: ' + str(e))
            finally:
                await page.close()

        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_anchor_parser())
