import json
import os
from datetime import datetime

import requests
from dateutil.relativedelta import relativedelta

from exact_dial import exact_dial
from propstream.propstream import PropStream
from util.util import dump_json_to_file


def get_base_url(county: str):
    return f"https://www.legacy.com/api/_frontend/localmarket/united-states/ohio/subregion/{county.lower()}-county"


county_vs_base_url_map = {
    "Butler": get_base_url("butler"),
    "Clermont": get_base_url("clermont"),
    "Hamilton": get_base_url("hamilton"),
    "Montgomery": get_base_url("montgomery"),
    "Warren": get_base_url("warren")
}


def get_clean_response(response_json, county):
    obituaries = response_json.get("obituaries")
    extracted_data = []
    for obituary in obituaries:
        info = {
            "personId": obituary["personId"],
            "first_name": obituary["name"]["firstName"],
            "last_name": obituary["name"]["lastName"],
            "middle_name": obituary["name"]["middleName"],
            "full_name": obituary["name"]["fullName"],
            "city": obituary["location"]["city"]["fullName"],
            "county": county,
            "state": obituary["location"]["state"]["fullName"],
            "details_url": obituary["links"]["obituaryUrl"]["href"]
        }
        extracted_data.append(info)

    return extracted_data


class LegacyDataCollector:
    PER_PAGE_LIMIT = 50

    def __init__(self, cf_clearance=None):
        self.start_date = (datetime.now() - relativedelta(months=1) + relativedelta(days=1)).strftime("%Y-%m-%d")
        self.end_date = datetime.now().strftime("%Y-%m-%d")
        self.session = requests.Session()
        self.session.headers = {
            'cookie': 'cf_clearance=' + cf_clearance,
            'referer': 'https://www.legacy.com/us/obituaries/local/ohio/butler-county',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0'
        }

        self.params = {
            "endDate": self.end_date,
            "startDate": self.start_date,
            "limit": self.PER_PAGE_LIMIT,
            "noticeType": "obituary",
            "sortBy": "date"
        }

    def collect_data_for_all_counties(self):
        all_data = {}
        for county in county_vs_base_url_map.keys():
            extracted_info = self.collect_data_for_county(county)
            if extracted_info:
                all_data[county] = extracted_info
        return all_data

    def collect_data_for_county(self, county):
        base_url = county_vs_base_url_map.get(county)
        if not base_url:
            print(f"Base URL not found for {county}")
            return None

        # if self.params contains offset then remove that key
        self.params.pop("offset", None)

        response = self.session.get(base_url, params=self.params)
        if response.status_code != 200:
            print(f"Error fetching data for {county}. Status code: {response.status_code}")
            return None

        first_response = response.json()
        total_records = first_response.get("totalRecordCount")
        # print(f"Total records for {county}: {total_records}")
        # show how many record is there to the user and ask if they want to continue
        answer = input(f'There are {total_records} records for {county}. Do you want to continue? (y/n): ')
        if answer.lower() != 'y':
            return None

        num_pages = total_records // self.PER_PAGE_LIMIT
        if (total_records % self.PER_PAGE_LIMIT) != 0:
            num_pages += 1

        obituaries = get_clean_response(first_response, county)

        for page in range(2, num_pages + 1):
            self.params["offset"] = (page - 1) * self.PER_PAGE_LIMIT
            response = self.session.get(base_url, params=self.params)
            if response.status_code != 200:
                print(f"Error fetching data for {county}. Status code: {response.status_code}")
                return None

            obituaries.extend(get_clean_response(response.json(), county))

        return obituaries


class LegacyExactDialPropStreamIntegrator:
    def __init__(self, start_date, end_date, legacy_data):
        self.start_date = start_date
        self.end_date = end_date
        self.data = legacy_data
        self.config = json.load(
            open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')))

    def update_from_exact_dial_and_prop_stream(self):

        if not self.data:
            print('No data to update')
            return

        try:
            self.ed_instance = exact_dial.ExactDial(user_email=self.config['exact_dial_email'],
                                                    password=self.config['exact_dial_password'])
        except Exception as e:
            print(f'Error occurred while initializing ExactDial instance: {e}')
            return

        try:
            self.propstream_instance = PropStream(username=self.config['propstream_email'],
                                                  password=self.config['propstream_password'])
        except Exception as e:
            print(f'Error occurred while initializing PropStream instance: {e}')
            return

        for county, data in self.data.items():
            self._collect_and_save(county, data)

    def _collect_and_save(self, county, data):
        for record in data:
            middle_name = ''
            if not record['middle_name'] is None:
                middle_name = record['middle_name']

            try:
                info = self.ed_instance.search_record(first_name=record['first_name'],
                                                      last_name=record['last_name'],
                                                      city=record['city'],
                                                      state=record['state'])

                current_address = ''
                if 'current_address' in info:
                    current_address = info['current_address']

                record['current_address'] = current_address

                relatives = info['relatives']
                if len(relatives) >= 3:
                    relatives = relatives[:3]

                for i, relative in enumerate(relatives):
                    record[f'relative_{i + 1}_name'] = relative['name']
                    numbers = relative['phone_numbers']

                    if len(numbers) >= 2:
                        numbers = numbers[:2]

                    for j, number in enumerate(numbers):
                        record[f'relative_{i + 1}_phone_number_{j + 1}'] = number['phone_number']
                        record[f'relative_{i + 1}_phone_number_{j + 1}_last_used_date'] = number['date']

                info = self._get_estimated_value_and_owner_info(current_address)
                if info:
                    record['propstream_data'] = info

                # if 'estimatedValue' in info:
                #     record['estimated_value'] = info['estimatedValue']


            except Exception as e:
                print(
                    f'Error occurred while extracting phone and email for {record["first_name"]} {record["last_name"]}: {e}')

        # create legacy data folder if not exists.
        if not os.path.exists('legacy data'):
            os.mkdir('legacy data')

        dump_json_to_file(data, os.path.join('legacy data',
                                             county + ' ' + self.start_date + ' - ' + self.end_date + '.json'))

    def _get_estimated_value_and_owner_info(self, address):
        if not address:
            return None

        # split by - from end and only remove the last instance of - from the address
        address = address.rsplit('-', 1)[0].strip()

        try:
            info = self.propstream_instance.search_property_estimated_value(address=address)
            if not info:
                return None

            return info

        except Exception as e:
            print(f'Error occurred while extracting estimated value for {address}: {e}')


# cf_clearance = (
#     'duFww2NkRvR_x2qGiu5o_Dp_IZ8X5wV5iVYqdz.987M-1731727144-1.2.1.1-sDGmktRMz9n7kpsWmgKbPR3ldaXQodW0G2bIxrA9OIY3HU9683.SoJIH.0niZZ78on4bUe1UwK...jN4GlaigERYiFF8ybGqsT8abe55NAB3naMbzOZ.xldmJYpmhCEFiypprH0GLYgaZI5rWk6TniNnTDcUZgerul3s3Q663OVJmDXCRBLUMb8hOis3WJf5hrCOajpV.a0nMAhZ7jOo_uojnm1GduaeCznvpuvSP8Bcn_xmnjP8rX5L8yBa.mxHM0TWf3.thKqTyCWMmWW52bArMITl3cHAathPl6hNMlIomqwEZuCHJYF8fjxeF0SfQGgavFHiU_mD8dk4myzhKxufN4nvQ.FdZEICAMUsprpxJpQomy5Z8oRVjrbozxM5LdsToYk5yFdqGebLpA4x1DU.9cLPNT6crzG5Px8fuGo6U0CtivPXXgDQNAwVWCOQ')

message = ('Open https://www.legacy.com/us/obituaries/local/ohio/butler-county and copy the cf_clearance cookie value '
           'and provide here:')
cf_clearance = input(message)

if not cf_clearance:
    print('cf_clearance value is required')
    exit(1)

legacy_data_collector = LegacyDataCollector(cf_clearance)
extracted_info = legacy_data_collector.collect_data_for_all_counties()
extracted_data = LegacyExactDialPropStreamIntegrator(legacy_data=extracted_info,
                                                     start_date=legacy_data_collector.start_date,
                                                     end_date=legacy_data_collector.end_date)

extracted_data.update_from_exact_dial_and_prop_stream()

# print(cf_clearance)
