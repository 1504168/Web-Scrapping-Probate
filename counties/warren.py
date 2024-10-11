import json
from datetime import datetime, timedelta

import bs4
import requests

from util.util import split_city_state_zip


class WarrenCounty:

    @staticmethod
    def _parse_date(date):
        # Assuming the date is in the format 'MM/DD/YYYY'
        month, day, year = date.split('/')
        return year, month, day

    @staticmethod
    def _create_payload(year, month, day):
        payload = {
            'name': '',
            'casenum': '',
            'fmonth': month,
            'fday': day,
            'fyear': year,
            'block': '250',
            'file_type': '4',
            'search_type': '9',
            'submit': 'Search',
            'agency_num': '8303'
        }
        return payload

    @staticmethod
    def _extract_case_links(response_text):

        soup = bs4.BeautifulSoup(response_text, 'html.parser')

        total_matches_text = soup.select_one('#cl_body > p > span > b').text
        if 'No Matches Displayed' in total_matches_text:
            return []

        print(f'Total matches: {total_matches_text}')
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
                if key == 'Fiduciary #1':
                    key = 'Fiduciary 1'

                value = b.next_sibling.strip()
                info_dict[key] = value

        if 'City/State/ZIP' in info_dict:
            city, state, zip_code = split_city_state_zip(info_dict['City/State/ZIP'])
            info_dict['City'] = city
            info_dict['State'] = state
            info_dict['Zip'] = zip_code

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
    def collect_data_for_range(start_date, end_date=None):

        if end_date is None:
            end_date = start_date

        start_date = datetime.strptime(start_date, '%m/%d/%Y')
        end_date = datetime.strptime(end_date, '%m/%d/%Y')

        session = requests.Session()

        all_decedent_info = []
        current_date = start_date
        while current_date <= end_date:
            print(f'Collecting data for {current_date.strftime("%m/%d/%Y")}')
            current_date_data = WarrenCounty._collect_data(current_date.strftime('%m/%d/%Y'), session)
            all_decedent_info.extend(current_date_data)
            current_date += timedelta(days=1)
        return all_decedent_info

    @staticmethod
    def _collect_data(date, session):
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
        print(f'Found {len(estate_links)} estate cases')

        all_case_details = []

        for estate_link in estate_links:
            all_case_details.append(WarrenCounty._collect_case_details(session, estate_link))

        return all_case_details


# estate_decedent_info = WarrenCounty.collect_data_for_range("09/30/2024", "10/10/2024")
#
# with open('../Extracted Data/Warren County.json', 'w') as f:
#     json.dump(estate_decedent_info, f, indent=4)
