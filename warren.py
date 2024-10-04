import json

import bs4
import requests


class WarrenCounty:

    @staticmethod
    def _parse_date(date):
        # Assuming the date is in the format 'YYYY-MM-DD'
        year, month, day = date.split('-')
        return year, month, day

    @staticmethod
    def _create_payload(year, month, day):
        payload = {
            'name': '',
            'casenum': '',
            'fmonth': month,
            'fday': day,
            'fyear': year,
            'block': '25',
            'file_type': '4',
            'search_type': '9',
            'submit': 'Search',
            'agency_num': '8303'
        }
        return payload

    @staticmethod
    def _extract_case_links(response_text):

        soup = bs4.BeautifulSoup(response_text, 'html.parser')
        table = soup.select_one('#cl_body > table')

        estate_case_links = []

        for tr in table.select('tr'):
            last_td = tr.select_one('td:last-child')
            # select text after Case Type: of td text
            if not 'Case Type:' in last_td.text:
                continue

            if last_td.text.split('Case Type: ')[1].rstrip() == 'Estate':
                case_link = last_td.select_one('a:nth-child(2)').get('href')
                estate_case_links.append(case_link)

        return estate_case_links

    @staticmethod
    def _extract_info_from_tr(current_tr):
        info_dict = {}

        for td in current_tr.find_all('td', {'class': 'back-lt'}):
            for b in td.find_all('b'):
                key = b.text.strip(': ')
                value = b.next_sibling.strip()
                info_dict[key] = value

        return info_dict

    @staticmethod
    def _collect_case_details(session, case_link):
        url = 'http://probate.co.warren.oh.us/cgi-bin/' + case_link
        headers = {
            'Origin': 'http://probate.co.warren.oh.us',
            'Referer': 'http://probate.co.warren.oh.us/cgi-bin/search.cgi'
        }

        response = session.request("GET", url, headers=headers)

        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        case_details = {"url": url}
        trs = soup.select_one("#cl_body > table > tr > tr").select("tr")
        decedent_info_tr = trs[1]
        fiduciary_info_tr = trs[3]
        case_details['decedent_info'] = WarrenCounty._extract_info_from_tr(decedent_info_tr)
        case_details['fiduciary_info'] = WarrenCounty._extract_info_from_tr(fiduciary_info_tr)

        return case_details

    @staticmethod
    def collect_data(date):
        session = requests.Session()
        # Expected date format is YYYY-MM-DD
        year, month, day = WarrenCounty._parse_date(date)
        payload = WarrenCounty._create_payload(year, month, day)
        url = "http://probate.co.warren.oh.us/cgi-bin/search.cgi"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'http://probate.co.warren.oh.us',
            'Referer': 'http://probate.co.warren.oh.us/search.php'
        }
        response = session.post(url, headers=headers, data=payload)
        estate_links = WarrenCounty._extract_case_links(response.text)

        all_case_details = []

        for estate_link in estate_links:
            all_case_details.append(WarrenCounty._collect_case_details(session, estate_link))

        return all_case_details


estate_decedent_info = WarrenCounty.collect_data("2024-09-30")

with open('Extracted Info/Warren County.json', 'w') as f:
    json.dump(estate_decedent_info, f, indent=4)
