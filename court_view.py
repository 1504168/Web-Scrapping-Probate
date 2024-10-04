import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait


class ClermontCounty:

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
    def _set_search_criteria(driver, date):
        year, month, day = date.split('-')
        formatted_date = month + '/' + day + '/' + year
        ClermontCounty._set_date(driver, 'fileDateRange:dateInputBegin', formatted_date)
        ClermontCounty._set_date(driver, 'fileDateRange:dateInputEnd', formatted_date)

        # select Estate, Open, Decedent
        ClermontCounty._select_item(driver, 'caseCd', 4)
        time.sleep(1)
        ClermontCounty._select_item(driver, 'statCd', 6)
        time.sleep(1)
        ClermontCounty._select_item(driver, 'ptyCd', 3)
        time.sleep(1)

    @staticmethod
    def _extract_current_case_details(driver, i):
        id = 'grid~row-' + str(i) + '~cell-2$link'
        case_href = driver.find_element(By.ID, id)
        case_number = case_href.text
        case_href.click()
        time.sleep(1)
        ClermontCounty._wait_for_element(driver, By.ID, 'ptyContainer')
        data_container = driver.find_element(By.ID, 'ptyContainer')
        address = driver.find_element(By.CLASS_NAME, 'ptyContactInfo').text.splitlines()
        decedent_and_applicant = [el.text for el in driver.find_elements(By.CLASS_NAME, 'ptyInfoLabel')]
        case_info = {'case_number': case_number, 'address': address[0], 'City/State/Zip': address[1],
                     'Decedent': decedent_and_applicant[0],
                     'Applicant': decedent_and_applicant[1]}
        driver.back()
        return case_info

    @staticmethod
    def collect_data(date):
        driver = webdriver.Chrome()
        ClermontCounty._goto_case_type_search_page(driver)

        ClermontCounty._set_search_criteria(driver, date)

        # click search button
        driver.find_element(By.NAME, 'submitLink').click()
        time.sleep(1)
        ClermontCounty._wait_for_element(driver, By.XPATH, '//*[@id="mainContent"]/div[2]/div[3]/div[1]/div[1]/span[1]')

        total_search_results = driver.find_element(By.XPATH,
                                                   '//*[@id="mainContent"]/div[2]/div[3]/div[1]/div[1]/span[1]').text
        print('Total search results:', total_search_results)

        all_case_hrefs = driver.find_elements(By.XPATH,
                                              "//a[contains(@id, 'grid~row-') and contains(@id, '~cell-2$link')]")
        total_cases = len(all_case_hrefs)
        all_case_info = []
        for i in range(1, total_cases + 1):
            case_info = ClermontCounty._extract_current_case_details(driver, i)
            all_case_info.append(case_info)

        # Remember to close the driver when you're done with it
        driver.quit()

        return all_case_info


ClermontCounty.collect_data('2024-10-03')
