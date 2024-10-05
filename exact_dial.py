import json

import bs4
import requests


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


def dump_json_to_file(data, file_name_or_path='Sample.json'):
    with open(file_name_or_path, 'w') as f:
        json.dump(data, f, indent=4)


def remove_parentheses(s):
    return s.replace('(', '').replace(')', '')


def extract_search_relatives_info(html_response):
    soup = bs4.BeautifulSoup(html_response, 'html.parser')
    relatives_div = soup.select_one('div.res_main_row_middle > div.col_last')
    #   keep only div and remove the first div
    relatives_div = relatives_div.find_all('div', recursive=False)[1:]
    #   Now first div has relative name and last second one has phone numbers. and it keep that pattern. I want to loop and extract all
    relatives_info = []
    for i in range(0, len(relatives_div), 2):
        relative_name = [remove_parentheses(idf) for idf in relatives_div[i].text.split('-')]
        phone_numbers = []

        for curr_div in relatives_div[i + 1].find_all('div', recursive=False):
            phone_number = [remove_parentheses(idf) for idf in
                            ' '.join(curr_div.text.replace('\xa0', '').split()).split()]
            phone_numbers.append(
                {'phone_identifier': next(iter(phone_number), ''),
                 'phone_number': next(iter(phone_number[1:]), ''),
                 'date': next(iter(phone_number[2:]), '')})

        relatives_info.append({'relative_identifier': relative_name[0], 'relative_name': relative_name[1],
                               'phone_numbers': phone_numbers})

    return relatives_info


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
            print('Login successful')
            self.token = extract_token(response.text)
            print('Token:', self.token)

    def search_record(self, first_name, last_name, city, state, address='', zip_code='', county=''):
        url = "https://app.exactdial.com/public/doSearch"

        payload = {'_token': self.token, 'firstName': first_name, 'lastName': last_name,
                   'address': address, 'city': city, 'state': state, 'nicknamesearch': 'on',
                   'middleName': '', 'phonenumber': '', 'zip': zip_code, 'county': county, 'dob': '', 'ageMin': '',
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
ed = ExactDial('Ibrahimfarhan444@gmail.com', 'chicago513')
dump_json_to_file(ed.search_record('Stephen', 'Davis', 'Troy', 'Ohio'), 'Sample.json')

# dump_json_to_file(extract_search_relatives_info(open('Sample.html').read()))