
# for converting to executable
# pyinstaller --onefile -n CourtDataExtractor main.py


import pandas as pd

from counties.clermont import ClermontCounty
from counties.ohio import OhioCounty
from counties.warren import WarrenCounty
from util.util import normalize_data


def collect_and_save_data_to_json(date):
    df = collect_all_county_data(date)
    file_name = 'Extracted Data/' + date.replace('/', '-') + '.json'
    print(f'Saving data to {file_name}')
    df.to_json(file_name, orient='records', indent=4)


def collect_all_county_data(date):
    dfs = []
    ohio_data = OhioCounty.collect_data(date)
    if ohio_data:
        ohio_data = normalize_data(ohio_data)
        ohio_data['county'] = 'Ohio'
        dfs.append(ohio_data)
        print(f'Ohio County data collected. Total cases: {len(ohio_data)}')

    warren_data = WarrenCounty.collect_data(date)
    if warren_data:
        warren_data = normalize_data(warren_data)
        warren_data['county'] = 'Warren'
        dfs.append(warren_data)
        print(f'Warren County data collected. Total cases: {len(warren_data)}')

    clermont_data = ClermontCounty.collect_data(date)
    if clermont_data:
        clermont_data = normalize_data(clermont_data)
        clermont_data['county'] = 'Clermont'
        dfs.append(clermont_data)
        print(f'Clermont County data collected. Total cases: {len(clermont_data)}')

    df = pd.concat(dfs, ignore_index=True)
    print(f'Total cases collected: {len(df)}')
    return df


if __name__ == '__main__':
    date = input('Enter the date in format MM/DD/YYYY: ')
    if not date:
        date = pd.Timestamp.now().strftime('%m/%d/%Y')

    print(f'Collecting data for {date}')
    collect_and_save_data_to_json(date)
