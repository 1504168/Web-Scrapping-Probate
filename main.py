import pandas as pd

from court_view import ClermontCounty
from ohio import OhioCounty
from util import normalize_data
from warren import WarrenCounty


def collect_all_county_data(date):
    dfs = []
    ohio_data = OhioCounty.collect_data(date)
    if ohio_data:
        dfs.append(normalize_data(ohio_data))

    warren_data = WarrenCounty.collect_data(date)
    if warren_data:
        dfs.append(normalize_data(warren_data))

    clermont_data = ClermontCounty.collect_data(date)
    if clermont_data:
        dfs.append(normalize_data(clermont_data))

    df = pd.concat(dfs, ignore_index=True)
    return df


df = collect_all_county_data('10/03/2024')

# Save the data to a CSV excel file
df.to_json('court_data.json', orient='records',indent=4)
