import base64
import json
from time import sleep

import requests
from selenium.webdriver.common.by import By
from seleniumwire import webdriver

from util.util import dump_json_to_file


def encode_password(password):
    # Convert the password string to bytes
    password_bytes = password.encode('utf-8')
    # Encode the bytes to Base64
    encoded_bytes = base64.b64encode(password_bytes)
    # Convert the encoded bytes back to a string
    encoded_password = encoded_bytes.decode('utf-8')
    return encoded_password


class PropStream:
    LOGIN_URL = 'https://login.propstream.com'

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._login()

    def search_property_estimated_value(self, address):
        if self.token is None:
            return

        url = "https://app.propstream.com/eqbackend/resource/auth/ps4/property/suggestionsnew"
        params = {'q': address}

        headers = {
            'referer': 'https://app.propstream.com/search',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
            'x-auth-token': self.token
        }

        response = self.session.request("GET", url, headers=headers, params=params)

        if response.status_code == 200:
            locations = response.json()
            if len(locations) == 1:
                params = {'id': locations[0]['id'], 'addressType': locations[0]['type'],
                          'streetAddress': locations[0]['streetAddress'], 'apn': locations[0]['apn'],
                          'cityId': locations[0]['cityId']}

                url = "https://app.propstream.com/eqbackend/resource/auth/ps4/property"
                headers = {
                    'referer': 'https://app.propstream.com/search',
                    'x-auth-token': self.token
                }

                response = requests.request("GET", url, headers=headers, params=params)
                if response.status_code == 200:
                    print("Property info is found for {}".format(address))
                    return response.json()['properties'][0]

        print("Property info is not found for {}".format(address))
        return None

    def _login(self):

        driver = webdriver.Chrome()
        driver.get(self.LOGIN_URL)

        driver.find_element(By.NAME, 'username').send_keys(self.username)
        driver.find_element(By.NAME, 'password').send_keys(self.password)
        driver.find_element(By.CSS_SELECTOR, '#form-content > form > button').click()

        reqs = [req for req in driver.requests if 'resource/auth?' in req.url]

        # wait for the login request to complete
        try_count = 0
        while (len(reqs) == 0):
            reqs = [req for req in driver.requests if 'resource/auth?' in req.url]
            sleep(1)
            try_count += 1
            if try_count > 10:
                break

        if len(reqs) == 1:
            reqs = [req for req in driver.requests if 'resource/auth?' in req.url]
            while reqs[0].response is None:
                reqs = [req for req in driver.requests if 'resource/auth?' in req.url]
                sleep(1)

            response_body = json.loads(reqs[0].response.body.decode('utf-8'))
            self.token = response_body['authToken']
            print('Successfully login to PopStream')


# ins = PropStream('Ibrahimfarhan444@gmail.com', 'Chicago513!')
# response = ins.search_property_estimated_value('5343 Sherry Lane, Fairfield, Oh 45014')
# response = ins.search_property_estimated_value('3326 Waterfowl Lane, Hamilton, Oh 45011')
# dump_json_to_file(response, 'Sample.json')
# test()
