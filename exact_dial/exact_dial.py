import pdb
from datetime import datetime

import bs4
import requests

from util.util import dump_json_to_file


def extract_search_id(html_response):
    soup = bs4.BeautifulSoup(html_response, 'html.parser')
    input_tag = soup.find('input', {'id': 'common_hidden_search_id'})
    value = input_tag['value'] if input_tag else None
    return value


def extract_token(html_response):
    soup = bs4.BeautifulSoup(html_response, 'html.parser')
    meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})
    token = meta_tag['content'] if meta_tag else None
    return token


def dump_to_file(text, file_name_or_path='Sample.html'):
    with open(file_name_or_path, 'w') as f:
        f.write(text)


def remove_parentheses(s):
    return s.replace('(', '').replace(')', '')


def extract_search_relatives_info(html_response):
    soup = bs4.BeautifulSoup(html_response, 'html.parser')
    phone_numbers_div = soup.select_one('div.res_main_row_middle > div.col_middle')

    if phone_numbers_div is None:
        print('No result found!')
        return {'current_address': '', 'phone_numbers': [], 'email': '', 'relatives': []}

    #   keep only div and remove the first div
    phone_numbers = get_clean_phone_numbers(phone_numbers_div)

    relatives_div = soup.select_one('div.res_main_row_middle > div.col_last')

    relative_info = get_relatives_phone_numbers(relatives_div)

    current_address = soup.select_one('div.res_main_row_top > div.col_last > div').text.split('Current Address:')[
        1].strip()

    email = \
        soup.select_one(
            'div.result_block_main > div > div.res_main_row_top > div.col_last > div:nth-child(2)').text.split(
            'Email Address:')[1].strip()

    return {'current_address': current_address, 'phone_numbers': phone_numbers, 'email': email,
            'relatives': relative_info}


def get_relatives_phone_numbers(relatives_div):
    relatives_div = relatives_div.find_all('div', recursive=False)[1:]
    phone_numbers = []

    # first div has relative identifer and second one has numbers. so we need to loop in steps of 2
    for i in range(0, len(relatives_div), 2):
        current_relative_info = {}
        current_relative_info['identifier'] = remove_parentheses(relatives_div[i].text.split('-')[0].strip())
        current_relative_info['name'] = relatives_div[i].text.split('-')[1].strip()
        divs = relatives_div[i + 1].find_all('div', recursive=False)
        numbers = [get_current_div_number(div) for div in divs]
        if numbers:
            numbers = [phone for phone in numbers if phone['phone_identifier'] == 'M']
            numbers = sorted(numbers,
                             key=lambda x: datetime.strptime(x['date'], '%m/%d/%Y') if x['date'] else datetime.min,
                             reverse=True)

            # if more than three phone numbers are found, keep only then sort by date and keep the latest three
            if len(numbers) > 3:
                numbers = numbers[:3]

            # remove phone_identifier
            for phone in numbers:
                phone.pop('phone_identifier')

        current_relative_info['phone_numbers'] = numbers
        phone_numbers.append(current_relative_info)

    return phone_numbers


def get_clean_phone_numbers(phone_numbers_div):
    phone_numbers_div = phone_numbers_div.find_all('div', recursive=False)[1:]
    phone_numbers = []
    for curr_div in phone_numbers_div:
        phone_numbers.append(get_current_div_number(curr_div))

    # keep only those object which has phone_identifier of 'M'
    if phone_numbers:
        phone_numbers = [phone for phone in phone_numbers if phone['phone_identifier'] == 'M']
        phone_numbers = sorted(phone_numbers,
                               key=lambda x: datetime.strptime(x['date'], '%m/%d/%Y') if x['date'] else datetime.min,
                               reverse=True)
    # if more than three phone numbers are found, keep only then sort by date and keep the latest three
    if len(phone_numbers) > 3:
        phone_numbers = phone_numbers[:3]
    # remove phone_identifier
    for phone in phone_numbers:
        phone.pop('phone_identifier')

    return phone_numbers


def get_current_div_number(curr_div):
    phone_number = [remove_parentheses(idf) for idf in
                    curr_div.text.replace('\xa0', ' ').split()]
    return {'phone_identifier': next(iter(phone_number), ''),
            'phone_number': next(iter(phone_number[1:]), ''),
            'date': next(iter(phone_number[2:]), '')}


class ExactDial():
    LOGIN_URL = 'https://app.exactdial.com/public/login'
    HOME_PAGE_URL = 'https://app.exactdial.com/public/home'

    def __init__(self, user_email, password):
        self.user_email = user_email
        self.password = password
        self.session = requests.Session()
        self._login()

    def _login(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0'
        }

        self.session.headers.update(headers)

        response = self.session.request("GET", self.LOGIN_URL)
        self.token = extract_token(response.text)

        payload = {'_token': self.token, 'email': self.user_email, 'password': self.password}

        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://app.exactdial.com',
            'referer': 'https://app.exactdial.com/public/login'
        }

        response = self.session.request("POST", self.LOGIN_URL, headers=headers, data=payload)

        if response.status_code == 200 and response.url == self.HOME_PAGE_URL:
            print('Logged into ExactDial successfully')
            self.token = extract_token(response.text)
            # print('Token:', self.token)

    def search_record(self, first_name, last_name, city, state, address='', zip_code='', county='', middle_name=''):
        url = "https://app.exactdial.com/public/doSearch"

        payload = {'_token': self.token, 'firstName': first_name, 'lastName': last_name,
                   'address': address, 'city': city, 'state': state, 'nicknamesearch': 'on',
                   'middleName': middle_name, 'phonenumber': '', 'zip': zip_code, 'county': county, 'dob': '',
                   'ageMin': '',
                   'ageMax': '', 'hid_search_type': '1', 'hid_redirect': 'home'}

        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://app.exactdial.com',
            'referer': 'https://app.exactdial.com/public/home'
        }

        response = self.session.request("POST", url, headers=headers, data=payload)

        payload = {
            'getSearchResult': '1'
            , 'all_data': '1'
            , 'record_no': '0'
            , 'search_ref_id': extract_search_id(response.text)
            , '_token': extract_token(response.text)
        }

        url = "https://app.exactdial.com/public/getSearchResult"

        headers = {
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://app.exactdial.com',
            'referer': 'https://app.exactdial.com/public/home',
            'x-requested-with': 'XMLHttpRequest'
        }

        response = self.session.request("POST", url, headers=headers, data=payload)

        dump_to_file(response.text, 'Sample.html')
        extracted_info = extract_search_relatives_info(response.text)
        return extracted_info

# create an instance of the class
# ed = ExactDial('Ibrahimfarhan444@gmail.com', 'chicago513')
# dump_json_to_file(ed.search_record('Stephen', 'Davis', 'Troy', 'Ohio'), 'Sample.json')
# dump_json_to_file(ed.search_record('GREGORY', 'ROTH', 'FAIRFIELD', 'Ohio',address='860 HICKS BLVD'), 'Sample2.json')

# dump_json_to_file(extract_search_relatives_info(open('Sample.html').read()), 'Sample2.json')
