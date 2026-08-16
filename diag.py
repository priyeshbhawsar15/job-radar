import asyncio
import json
import httpx

async def test_workday_cxs():
    print('=== TYPE 1: WORKDAY CXS API DIAGNOSTIC ===')
    test_urls = [
        ('Walmart', 'https://walmart.wd504.myworkdayjobs.com/wday/cxs/walmart/WalmartExternal/jobs', {'appliedFacets': {'locationCountry': ['bc21272661f045c48b4562095f54911d']}, 'limit': 20, 'offset': 0}),
        ('Adobe', 'https://adobe.wd5.myworkdayjobs.com/wday/cxs/adobe/external_experienced/jobs', {'appliedFacets': {}, 'limit': 20, 'offset': 0}),
        ('eBay', 'https://ebay.wd1.myworkdayjobs.com/wday/cxs/ebay/apply/jobs', {'appliedFacets': {}, 'limit': 20, 'offset': 0})
    ]

    async with httpx.AsyncClient(timeout=10.0, headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json', 'Accept': 'application/json'}) as client:
        for name, endpoint, payload in test_urls:
            try:
                resp = await client.post(endpoint, json=payload)
                print(name + ' POST ' + endpoint + ' -> Status: ' + str(resp.status_code))
                if resp.status_code == 200:
                    data = resp.json()
                    total = data.get('total', 0)
                    postings = len(data.get('jobPostings', []))
                    print('  ✓ SUCCESS: ' + str(total) + ' total jobs found in Workday CXS API! (' + str(postings) + ' in page 1)')
                else:
                    print('  ✗ Status ' + str(resp.status_code) + ': ' + resp.text[:150])
            except Exception as e:
                print('  ✗ Error: ' + str(e))

async def test_type2_apis():
    print('=== TYPE 2: CLIENT-SIDE JS API DIAGNOSTICS ===')
    apis = [
        ('Amazon', 'https://www.amazon.jobs/en/search.json?base_query=&category[]=software-development&country[]=IND', 'GET'),
        ('Microsoft', 'https://careers.microsoft.com/api/pcsx/search?domain=microsoft.com&lc=en-us&q=software', 'GET'),
        ('RBCTech', 'https://aligncrm.stratsy.us/api/public/opportunities', 'GET'),
        ('Celonis', 'https://dxp-api.celonis.com/v1/jobs?location=India', 'GET'),
        ('Vanguard', 'https://jobsapi-google.m-cloud.io/api/job/search?companyName=companies%2Fvanguard', 'GET')
    ]

    async with httpx.AsyncClient(timeout=10.0, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}) as client:
        for name, url, method in apis:
            try:
                resp = await client.get(url)
                print(name + ' GET ' + url[:60] + '... -> Status: ' + str(resp.status_code))
                if resp.status_code == 200:
                    print('  ✓ SUCCESS: Received JSON response (' + str(len(resp.content)) + ' bytes)')
                else:
                    print('  ✗ Status ' + str(resp.status_code) + ': ' + resp.text[:100])
            except Exception as e:
                print('  ✗ Error: ' + str(e))

async def main():
    await test_workday_cxs()
    await test_type2_apis()

if __name__ == '__main__':
    asyncio.run(main())
