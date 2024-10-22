# for converting to executable
# pyinstaller --onefile -n CourtDataExtractor main.py
# for Mac universal: pyinstaller --onefile -n CourtDataExtractor main.py --target-arch=universal2
# for Mac intel: pyinstaller --onefile -n CourtDataExtractor main.py --target-arch=x86_64
# for Mac arm: pyinstaller --onefile -n CourtDataExtractor main.py --target-arch=arm64

import json
import os
import sys

import pandas as pd

from counties.butler import OhioCounty
from counties.clermont import ClermontCounty
from counties.warren import WarrenCounty
from exact_dial import exact_dial
from util.util import normalize_data


def collect_and_save_data_to_json(start_date, end_date, executable_location):
    df = collect_all_county_data(start_date, end_date, executable_location)
    if df is None:
        return
    file_name = os.path.join(executable_location, 'Extracted Data', start_date.replace('/', '-') + '.json')
    print(f'Saving data to {file_name}')
    df.to_json(file_name, orient='records', indent=4)


def split_name(full_name):
    names = full_name.split(',')
    if len(names) == 2:
        first_name = names[1].strip().split(' ')[0]
        last_name = names[0].strip()
        return first_name, last_name

    return None, None


def extract_phone_and_email_from_exact_dial(df, executable_location):
    config = json.load(open(os.path.join(executable_location, 'config.json')))

    ed_instance = exact_dial.ExactDial(user_email=config['exact_dial_email'],
                                       password=config['exact_dial_password'])

    # loop through each row in the dataframe
    for index, row in df.iterrows():
        # get fiduciary_info from the row
        first_name, last_name = split_name(row['fiduciary_info.Fiduciary 1'])
        print(f'Extracting phone and email for {first_name} {last_name}')
        city = row['fiduciary_info.City']
        state = row['fiduciary_info.State']
        zip_code = row['fiduciary_info.Zip']
        address = row['fiduciary_info.Address']
        info = ed_instance.search_record(first_name, last_name, city, state, address, zip_code)
        df.at[index, 'exact_dial_Fiduciary 1_email_address'] = info['email']

        phone_numbers = info['phone_numbers']
        for i, phone in enumerate(phone_numbers):
            df.at[index, f'exact_dial_Fiduciary 1_phone_number_{i + 1}'] = phone['phone_number']
            df.at[index, f'exact_dial_Fiduciary 1_phone_number_{i + 1}_identifier'] = phone['phone_identifier']
            df.at[index, f'exact_dial_Fiduciary 1_phone_number_{i + 1}_last_used_date'] = phone['date']

    return df


def collect_all_county_data(start_date, end_date, executable_location):
    dfs = []
    ohio_data = OhioCounty.collect_data_for_range(start_date, end_date)
    if ohio_data:
        ohio_data = normalize_data(ohio_data)
        ohio_data['county'] = 'Butler'
        dfs.append(ohio_data)
        print(f'Ohio County data collected. Total cases: {len(ohio_data)}')

    warren_data = WarrenCounty.collect_data_for_range(start_date, end_date)
    if warren_data:
        warren_data = normalize_data(warren_data)
        warren_data['county'] = 'Warren'
        dfs.append(warren_data)
        print(f'Warren County data collected. Total cases: {len(warren_data)}')

    clermont_data = ClermontCounty.collect_data_for_range(start_date, end_date)
    if clermont_data:
        clermont_data = normalize_data(clermont_data)
        clermont_data['county'] = 'Clermont'
        dfs.append(clermont_data)
        print(f'Clermont County data collected. Total cases: {len(clermont_data)}')

    if not dfs:
        print('No data found for date provided.')
        return None

    df = pd.concat(dfs, ignore_index=True)
    print(f'Total cases collected: {len(df)}')
    df = extract_phone_and_email_from_exact_dial(df, executable_location)
    return df


def get_executable_folder_location():
    folder_path = ''
    if getattr(sys, 'frozen', False):
        folder_path = os.path.dirname(sys.executable)
    else:
        folder_path = os.path.dirname(os.path.abspath(__file__))

    return folder_path


if __name__ == '__main__':
    executable_location = get_executable_folder_location()
    print(f'Executable location: {executable_location}')
    start_date = input('Enter the start date in format MM/DD/YYYY: ')
    if not start_date:
        start_date = pd.Timestamp.now().strftime('%m/%d/%Y')

    end_date = input('Enter the end date in format MM/DD/YYYY: ')
    if not end_date:
        end_date = start_date

    print(f'Collecting data for {start_date} to {end_date}')
    collect_and_save_data_to_json(start_date, end_date, executable_location)
