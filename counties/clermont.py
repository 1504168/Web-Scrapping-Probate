import json
import re
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

from util.util import split_city_state_zip, format_date


class ClermontCounty:

    @staticmethod
    def collect_data_for_range(start_date, end_date=None):

        if end_date is None:
            end_date = start_date

        driver = webdriver.Chrome()
        ClermontCounty._goto_case_type_search_page(driver)

        ClermontCounty._set_search_criteria(driver, start_date, end_date)

        # click search button
        driver.find_element(By.NAME, 'submitLink').click()
        time.sleep(1)

        try:
            ClermontCounty._wait_for_element(driver, By.ID, 'srchResultNoticeNomatch', 3)
            no_result_el = driver.find_element(By.ID, 'srchResultNoticeNomatch')
            print('No search results found in Clermont county.')
            return []
        except Exception:
            print('Search results found in Clermont county.')

        ClermontCounty._wait_for_element(driver, By.XPATH, '//*[@id="mainContent"]/div[2]/div[3]/div[1]/div[1]/span[1]')

        total_search_results = driver.find_element(By.XPATH,
                                                   '//*[@id="mainContent"]/div[2]/div[3]/div[1]/div[1]/span[1]').text

        # Extract the total number of search results
        matches = re.findall(r'\d+', total_search_results)
        total_search_results = int(matches[-1]) if matches else 0

        # Calculate the total number of pages
        total_pages = (total_search_results + 49) // 50

        print('Total search results:', total_search_results, 'Total pages:', total_pages)

        all_case_info = []

        count = 0
        # Process the search results in batches of 50
        for page in range(total_pages):

            # Process a batch of 50 results
            if page > 0:
                ClermontCounty.click_on_correct_page(driver, page + 1)

            all_case_hrefs = driver.find_elements(By.XPATH,
                                                  "//a[contains(@id, 'grid~row-') and contains(@id, '~cell-2$link')]")
            total_cases = len(all_case_hrefs)
            for i in range(total_cases):

                if page > 0:
                    ClermontCounty.click_on_correct_page(driver, page + 1)

                case_info = ClermontCounty._extract_current_case_details(driver, i)
                all_case_info.append(case_info)
                count += 1
                print('Case:', count, 'Case Number:', case_info['case_number'])

        # Remember to close the driver when you're done with it
        driver.quit()

        return all_case_info

    @staticmethod
    def click_on_correct_page(driver, page_number):
        page_number = str(page_number)
        try:
            page_button = driver.find_element(By.XPATH, f'//a[@title="Go to page {page_number}"]')
            page_button.click()
            time.sleep(1)
        except Exception:
            print('Error clicking on page:', page_number)

    @staticmethod
    def _wait_for_element(driver, by, element_identifier, time_out=10):
        WebDriverWait(driver, time_out).until(EC.presence_of_element_located((by, element_identifier)))

    @staticmethod
    def _set_date(driver, element_name, date):
        driver.find_element(By.NAME, element_name).clear()
        driver.find_element(By.NAME, element_name).send_keys(date)

    @staticmethod
    def _select_item(driver, element_name, item_index):
        select_element = driver.find_element(By.NAME, element_name)
        select = Select(select_element)
        try:
            # Attempt to clear old selection
            select.deselect_all()
        except NotImplementedError:
            # Ignore exception if deselect_all() is not supported
            pass

        select.select_by_index(item_index)
        # select.options[item_index].click()

    @staticmethod
    def _goto_case_type_search_page(driver):
        driver.get("https://eservices.clermontclerk.org/probate/search.page")

        ACCEPT_BUTTON_ID = 'id2f'
        ClermontCounty._wait_for_element(driver, By.ID, ACCEPT_BUTTON_ID)
        driver.find_element(By.ID, ACCEPT_BUTTON_ID).click()

        ClermontCounty._wait_for_element(driver, By.ID, 'searchPageTabSection')
        CASE_TYPE_XPATH = '//*[@id="searchPageTabSection"]/div[1]/div[1]/ul/li[2]/a[1]'
        driver.find_element(By.XPATH, CASE_TYPE_XPATH).click()
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, 'fileDateRange:dateInputBegin')))
        time.sleep(1)

    @staticmethod
    def _set_search_criteria(driver, start_date, end_date):
        ClermontCounty._set_date(driver, 'fileDateRange:dateInputBegin', format_date(start_date))
        ClermontCounty._set_date(driver, 'fileDateRange:dateInputEnd', format_date(end_date))

        # select Estate, Open, Decedent
        ClermontCounty._select_item(driver, 'caseCd', 4)
        time.sleep(1)
        ClermontCounty._select_item(driver, 'statCd', 6)
        time.sleep(1)
        ClermontCounty._select_item(driver, 'ptyCd', 3)
        time.sleep(1)

    @staticmethod
    def _extract_current_case_details(driver, i):

        all_case_hrefs = driver.find_elements(By.XPATH,
                                              "//a[contains(@id, 'grid~row-') and contains(@id, '~cell-2$link')]")

        # id = 'grid~row-' + str(i) + '~cell-2$link'
        case_href = all_case_hrefs[i]
        case_number = case_href.text
        case_href.click()
        time.sleep(1)
        ClermontCounty._wait_for_element(driver, By.ID, 'ptyContainer')
        data_container = driver.find_element(By.ID, 'ptyContainer')
        address = driver.find_elements(By.CLASS_NAME, 'ptyContactInfo')[0:2]
        address = [el.text.splitlines() for el in address]
        decedent_and_applicant = [el.text for el in driver.find_elements(By.CLASS_NAME, 'ptyInfoLabel')]

        decedent_info = {'Decedent': decedent_and_applicant[0], 'Address': None,
                         'City/State/ZIP': None, 'City': None, 'State': None, 'Zip': None}
        if len(address) > 0:
            city, state, zip_code = split_city_state_zip(address[0][1])
            decedent_info['Address'] = address[0][0]
            decedent_info['City/State/ZIP'] = address[0][1]
            decedent_info['City'] = city
            decedent_info['State'] = state
            decedent_info['Zip'] = zip_code

        fiduciary_info = {'Fiduciary 1': decedent_and_applicant[1], 'Address': None,
                          'City/State/ZIP': None, 'City': None, 'State': None, 'Zip': None}

        if len(address) > 1:
            city, state, zip_code = split_city_state_zip(address[1][1])
            fiduciary_info['Address'] = address[1][0]
            fiduciary_info['City/State/ZIP'] = address[1][1]
            fiduciary_info['City'] = city
            fiduciary_info['State'] = state
            fiduciary_info['Zip'] = zip_code

        case_info = {'case_number': case_number,
                     'decedent_info': decedent_info,
                     'fiduciary_info': fiduciary_info
                     }
        driver.back()
        return case_info


# extracted_info = ClermontCounty.collect_data_for_range('06/01/2024', '10/10/2024')
#
# with open('../Extracted Data/clermont_county_data.json', 'w') as f:
#     json.dump(extracted_info, f, indent=4)
