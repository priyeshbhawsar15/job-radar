import asyncio
import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright

def generate_fingerprint(company: str, title: str, location: str = None) -> str:
    return "fp"

def extract_html_job_links(html: str, board_name: str, target_url: str):
    results = []
    seen_urls = set()
    parsed_target = urlparse(target_url)

    job_path_keywords = [
        '/job/', '/jobs/', '/careers/job/', 'gh_jid=', '/posting/', '/opportunities/',
        '/job_details/', '/job-detail/', '/careers-list/', '/open-roles/', 'R-'
    ]

    matches = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)

    for href, inner in matches:
        href_lower = href.lower()
        is_job = any(k in href_lower for k in job_path_keywords) or bool(re.search(r'R-\d+|_R\d+|/job_details/\d+|/jobs/results/\d+|/jobs/[0-9a-f\-]{10,}', href_lower))
        if not is_job:
            continue

        if any(x in href_lower for x in ['search', 'privacy', 'terms', 'login', 'signin', 'cookie', 'gstatic', 'facebook.com', 'twitter.com', 'linkedin.com', 'recommendations', 'saved', 'alerts']):
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

        if clean_url in seen_urls or clean_url.rstrip('/') == target_url.rstrip('/'):
            continue
        seen_urls.add(clean_url)

        clean_text = re.sub(r'<[^>]+>', ' ', inner).strip()
        clean_text = ' '.join(clean_text.split())

        if clean_text and len(clean_text) > 3 and not any(x in clean_text.lower() for x in ['apply', 'view', 'read more', 'learn more', 'details', 'work_outline']):
            title = clean_text.split(' ⋅ ')[0].split(' Bangalore')[0].split(' India')[0].strip()
        else:
            slug = clean_url.rstrip('/').split('/')[-1]
            slug_clean = re.sub(r'^[0-9a-f\-]+[-_]', '', slug).replace('-', ' ').replace('_', ' ').title()
            title = slug_clean if len(slug_clean) > 3 else f"Position at {board_name}"

        results.append((title, clean_url))

    return results

async def test_all_parsed_titles():
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

                extracted = extract_html_job_links(html, name, url)
                print(f'=== {name}: Extracted {len(extracted)} clean jobs ===')
                for t, u in extracted[:4]:
                    print(f'  ✓ Title: "{t}" | URL: {u[:80]}')
            except Exception as e:
                print(name + ' -> Error: ' + str(e))
            finally:
                await page.close()

        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_all_parsed_titles())
