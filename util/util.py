import json

import pandas as pd


def split_city_state_zip(address):
    # Sample Address: Cincinnati, OH 45244
    if address is None:
        return None, None, None

    city_state_zip = address.split(',')
    city = city_state_zip[0].strip()
    state_zip = ''

    if len(city_state_zip) > 1:
        state_zip = city_state_zip[1].strip()

    state, zip_code = None, None
    if ' ' in state_zip:
        state, zip_code = state_zip.split(' ')
    else:
        state = state_zip
    return city, state, zip_code


def normalize_data(data):
    # Convert the data to a DataFrame to get the column names
    df = pd.DataFrame(data)

    # Get the column names excluding the nested objects
    columns = [col for col in df.columns if col not in ['decedent_info', 'fiduciary_info']]

    # Ensure 'decedent_info' and 'fiduciary_info' are lists of dictionaries
    for item in data:
        item['decedent_info'] = [item['decedent_info']]
        item['fiduciary_info'] = [item['fiduciary_info']]

    # Normalize the 'decedent_info' data
    df_decedent_info = pd.json_normalize(data, 'decedent_info', columns, record_prefix='decedent_info.')

    # Normalize the 'fiduciary_info' data
    df_fiduciary_info = pd.json_normalize(data, 'fiduciary_info', columns, record_prefix='fiduciary_info.')

    # Merge the two DataFrames on the common columns
    df_final = pd.merge(df_decedent_info, df_fiduciary_info, on=columns)

    return df_final


def format_date(date):
    month, day, year = date.split('/')
    return month.zfill(2) + '/' + day.zfill(2) + '/' + year.zfill(4)


def format_phone_number(phone_number):
    # Remove parentheses
    phone_number = phone_number.replace('(', '').replace(')', '')
    # Replace spaces with hyphens
    phone_number = phone_number.replace(' ', '-')
    return phone_number


def dump_json_to_file(data, file_name_or_path='Sample.json'):
    with open(file_name_or_path, 'w') as f:
        json.dump(data, f, indent=4)
