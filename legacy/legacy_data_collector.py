import json
from datetime import datetime

import requests
from dateutil.relativedelta import relativedelta


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
        self.session = requests.Session()
        self.session.headers = {
            'cookie': 'cf_clearance=' + cf_clearance,
            'referer': 'https://www.legacy.com/us/obituaries/local/ohio/butler-county',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0'
        }

        self.params = {
            "endDate": datetime.now().strftime("%Y-%m-%d"),
            "startDate": (datetime.now() - relativedelta(months=1) + relativedelta(days=1)).strftime("%Y-%m-%d"),
            "limit": self.PER_PAGE_LIMIT,
            "noticeType": "obituary",
            "sortBy": "date"
        }

    def collect_data_for_all_counties(self):
        all_data = []
        for county in county_vs_base_url_map.keys():
            extracted_info = self.collect_data_for_county(county)
            if extracted_info:
                all_data.extend(extracted_info)
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
        print(f"Total records for {county}: {total_records}")
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


cf_clearance = 'J_jboQc1XI14LhTu3_u9Pa5cDmmX7W8SNIs6fj4vLv0-1731437822-1.2.1.1-z3Oc76TEXE6D3jaXbSMd2kT15PV1D_DiAk_RYaOq1Z3u_g6femYN8MdkRgjbYaF4ek5LZUy3DWskNFVGsL.P1KzjYIZN5JMgU31Wx5V_6alz.hUBTALyyjZGiVhqHAHLHGWt8SFAv3IbusWusrA3KX7GrRJGNjKnnOBovJwrw9YbxzjbQGGcWQYuPSqlY39NItKIr_dlT1NqBW1sRAHVu4FXEuFYsGOG7VQCx2QyiLJxEHq6B3OT9qYnVFKlF5VWr1uIe1RU5bExKiUTRlTw56zAWZaItIBUnovMQXzC8f6g.wLlEVVBltu_6G..BS_vhy6eiSW7h40vwaNaYsWGrAjIGLUrcWbr7C_pBpMexLY7UyHT0H5oyK5aHqRojnDCy006ZTHjG31quc367GP891kILfEDokHyAxyX3LNOO5ltwV2.MKDTPCz615edYGNa'

test = LegacyDataCollector(cf_clearance)
extracted_info = test.collect_data_for_all_counties()

with open("legacy_data.json", "w") as f:
    json.dump(extracted_info, f, indent=4)
