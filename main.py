import json

import bs4
import requests

OHIO_COURT_SEARCH_URL = "https://probatecourt.bcohio.gov/recordSearch.php"
ACCEPT_CONTINUE_URL = "https://probatecourt.bcohio.gov/recordSearch.php?k=acceptAgreementsearchForm0909"

session = requests.Session()


def get_common_headers(cookies):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
        'Cookie': 'PHPSESSID=' + cookies['PHPSESSID'] + '; haTestCookie=' + cookies['haTestCookie']
    }
    return headers


def update_cookies():
    response = session.get(OHIO_COURT_SEARCH_URL)
    session.headers.update(get_common_headers(response.cookies.get_dict()))


def accept_continue():
    payload = {}
    response = session.request("GET", ACCEPT_CONTINUE_URL, headers={'Referer': OHIO_COURT_SEARCH_URL}, data=payload)
    if '<input type="hidden" name="k" id="k" value="' in response.text:
        return response.text.split('<input type="hidden" name="k" id="k" value="')[1].split('"')[0]
    else:
        return None


def extract_descendant_info(info_table):
    descendant_info = {}
    for tr in info_table.select('tr'):
        NON_BREAKING_SPACE = '\xa0'
        if tr.select_one('th.column1').text != NON_BREAKING_SPACE:
            descendant_info[tr.select_one('th.column1').text] = tr.select_one('td.column2').text

        if tr.select_one('th.column3').text != NON_BREAKING_SPACE:
            descendant_info[tr.select_one('th.column3').text] = tr.select_one('td.column4').text

    return descendant_info


def get_current_descendant_info(relative_url):
    url = 'https://probatecourt.bcohio.gov' + relative_url
    payload = {}
    response = session.request("GET", url, headers={'Referer': OHIO_COURT_SEARCH_URL}, data=payload)
    soup = bs4.BeautifulSoup(response.text, 'html.parser')

    extracted_info = {'url': url}
    descendant_info_table = soup.select_one('#caseInformation > tr:nth-child(2) > td > div > table')
    extracted_info['descendant_info'] = extract_descendant_info(descendant_info_table)
    fiduciary_info_table = soup.select_one('#caseInformation > tr:nth-child(4) > td > div > table')
    extracted_info['fiduciary_info'] = extract_descendant_info(fiduciary_info_table)

    return extracted_info


def get_search_results(k, day_num, month_num, year_num):
    payload = {'searchName': '', 'searchCase': '', 'searchFMonth': str(month_num), 'searchFDay': str(day_num),
               'searchFYear': str(year_num),
               'searchAgency[]': '0909', 'searchCaseType[]': 'PE', 'searchBlock': '25',
               'searchType': 'mainSearch', 'k': k}

    headers = {
        'Referer': 'https://probatecourt.bcohio.gov/recordSearch.php?k=acceptAgreementsearchForm0909',
        "Origin": 'https://probatecourt.bcohio.gov', 'Content-Type': 'application/x-www-form-urlencoded'}

    response = session.request("POST", OHIO_COURT_SEARCH_URL, headers=headers, data=payload)

    #     use bs4 to parse the response and select items which is under the id 'searchResults'
    soup = bs4.BeautifulSoup(response.text, 'html.parser')
    # Select all children of #searchResults
    children = soup.select('#searchResults > div')

    # For each child, select div.caseInfo > a.caseLink.icon
    links = [child.select_one('div.caseInfo > a.caseLink.icon').get('href') for child in children]
    all_descendant_info = [get_current_descendant_info(link) for link in links]

    return all_descendant_info


update_cookies()
k = accept_continue()
all_descendant_info = get_search_results(k, 30, 9, 2024)
# dump the extracted info to a json file

with open('descendant_info.json', 'w') as f:
    json.dump(all_descendant_info, f, indent=4)
