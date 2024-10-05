import bs4
import requests

from util import split_city_state_zip


class OhioCounty:
    OHIO_COURT_SEARCH_URL = "https://probatecourt.bcohio.gov/recordSearch.php"
    ACCEPT_CONTINUE_URL = "https://probatecourt.bcohio.gov/recordSearch.php?k=acceptAgreementsearchForm0909"

    @staticmethod
    def collect_data(date):

        year, month, day = OhioCounty._parse_date(date)
        session = requests.Session()
        OhioCounty._update_cookies(session)
        k = OhioCounty._accept_continue(session)

        payload = {'searchName': '', 'searchCase': '', 'searchFMonth': str(month), 'searchFDay': day,
                   'searchFYear': year,
                   'searchAgency[]': '0909', 'searchCaseType[]': 'PE', 'searchBlock': '100',
                   'searchType': 'mainSearch', 'k': k}

        headers = {
            'Referer': 'https://probatecourt.bcohio.gov/recordSearch.php?k=acceptAgreementsearchForm0909',
            "Origin": 'https://probatecourt.bcohio.gov', 'Content-Type': 'application/x-www-form-urlencoded'}

        response = session.request("POST", OhioCounty.OHIO_COURT_SEARCH_URL, headers=headers, data=payload)

        #     use bs4 to parse the response and select items which is under the id 'searchResults'
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        total_matches = int(soup.select_one('#matchCount').text.split()[0])
        print(f'Total matches: {total_matches}')
        if total_matches == 0:
            return []

        # Select all children of #searchResults
        children = soup.select('#searchResults > div')

        # For each child, select div.caseInfo > a.caseLink.icon
        links = [child.select_one('div.caseInfo > a.caseLink.icon').get('href') for child in children]
        all_decedent_info = [OhioCounty._get_current_decedent_info(session, link) for link in links]

        return all_decedent_info

    @staticmethod
    def _parse_date(date):
        # Assuming the date is in the format 'MM/DD/YYYY'
        month, day, year = date.split('/')
        return year, month, day

    @staticmethod
    def _get_common_headers(cookies):
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                      '*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
            'Cookie': 'PHPSESSID=' + cookies['PHPSESSID'] + '; haTestCookie=' + cookies['haTestCookie']
        }
        return headers

    @staticmethod
    def _update_cookies(session):
        response = session.get(OhioCounty.OHIO_COURT_SEARCH_URL)
        session.headers.update(OhioCounty._get_common_headers(response.cookies.get_dict()))

    @staticmethod
    def _accept_continue(session):
        payload = {}
        response = session.request("GET", OhioCounty.ACCEPT_CONTINUE_URL,
                                   headers={'Referer': OhioCounty.OHIO_COURT_SEARCH_URL}, data=payload)
        if '<input type="hidden" name="k" id="k" value="' in response.text:
            return response.text.split('<input type="hidden" name="k" id="k" value="')[1].split('"')[0]
        else:
            return None

    @staticmethod
    def _extract_info(info_table):
        decedent_info = {}
        for tr in info_table.select('tr'):
            NON_BREAKING_SPACE = '\xa0'
            if tr.select_one('th.column1').text != NON_BREAKING_SPACE:
                decedent_info[tr.select_one('th.column1').text] = tr.select_one('td.column2').text

            if tr.select_one('th.column3').text != NON_BREAKING_SPACE:
                decedent_info[tr.select_one('th.column3').text] = tr.select_one('td.column4').text

        if 'City/State/ZIP:' in decedent_info:
            city, state, zip_code = split_city_state_zip(decedent_info['City/State/ZIP:'])
            decedent_info['City'] = city
            decedent_info['State'] = state
            decedent_info['Zip'] = zip_code

        # remove ending : from the keys only if exist
        decedent_info = {k[:-1] if k[-1] == ':' else k: v for k, v in decedent_info.items()}

        if 'Phone Number' in decedent_info:
            decedent_info['Telephone'] = decedent_info['Phone Number']
            del decedent_info['Phone Number']

        return decedent_info

    @staticmethod
    def _get_current_decedent_info(session, relative_url):
        url = 'https://probatecourt.bcohio.gov' + relative_url
        payload = {}
        response = session.request("GET", url, headers={'Referer': OhioCounty.OHIO_COURT_SEARCH_URL}, data=payload)
        soup = bs4.BeautifulSoup(response.text, 'html.parser')

        extracted_info = {'url': url}
        decedent_info_table = soup.select_one('#caseInformation > tr:nth-child(2) > td > div > table')
        extracted_info['decedent_info'] = OhioCounty._extract_info(decedent_info_table)
        fiduciary_info_table = soup.select_one('#caseInformation > tr:nth-child(4) > td > div > table')
        extracted_info['fiduciary_info'] = OhioCounty._extract_info(fiduciary_info_table)

        return extracted_info

# estate_decedent_info = OhioCounty.collect_data("09/30/2024")
#
# with open('Extracted Info/Ohio County.json', 'w') as f:
#     json.dump(estate_decedent_info, f, indent=4)
