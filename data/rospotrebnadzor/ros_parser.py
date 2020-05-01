import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import requests
import pandas as pd
import numpy as np
import re


class RegionMatcher:
    """
    Ironing out disrepances between RosPotrebNadzor labels and iso_alpha3 codes.
    """

    def get_simplified_region(self, x):
        x = x.lower()
        x = (
            x.replace("край", "")
            .replace("область", "")
            .replace("республика", "")
            .replace(" ао", "")
            .replace("г.", "")
        )
        return x.split()[0]

    def collect_region_update(self, table_soup, region_df):
        matches = [
            re.findall("\d+\.\s+(.*)\s-\s(\d+)", x.text)
            for x in table_soup.find_all("p")
        ]
        # different formatting every day
        matches = [x for x in np.array(matches).flatten() if len(x) > 0]
        matches = [x[0] if isinstance(x, list) else x for x in matches]
        # to simplified format
        matches = [(x[0].lower(), int(x[1])) for x in matches]
        matches = [(self.get_simplified_region(x[0]), x[1]) for x in matches]
        # extracting iso codes
        iso_codes = region_df.set_index("name")["iso_code"].to_dict()
        iso_codes = {self.get_simplified_region(x): iso_codes[x] for x in iso_codes}
        matched_codes = [(iso_codes[x[0]], x[1]) for x in matches]
        # finding the last date
        date = table_soup.find("p", {"class": "date"})
        date = datetime.strptime(date.text[:-3], "%d.%m.%Y").strftime("%Y-%m-%d")
        update_df = pd.DataFrame(matched_codes)
        update_df.columns = ["region", "confirmed"]
        update_df["date"] = date
        return update_df


class ReportDownloader:
    def __init__(self, cfg):
        self.cfg = cfg

    def get_latest_info(self):
        rospage_response = requests.get(self.cfg["rospotreb_page"] + "about/info/news/")
        main_page_content = rospage_response.content.decode("Windows-1251")
        soup = BeautifulSoup(main_page_content, "html.parser")
        link = (
            self.cfg["rospotreb_page"]
            + soup.find(
                "a",
                text=" О подтвержденных случаях новой коронавирусной инфекции COVID-2019 в России",
            )["href"]
        )
        last_report_response = requests.get(link)
        report = last_report_response.content.decode("Windows-1251")
        soup = BeautifulSoup(report, "html.parser")
        div = soup.find("div", {"class": "news-detail"})
        return div

    def download_report(self):
        confirmed_cases = pd.read_csv(self.cfg["timeseries_page"])
        last_update = self.get_latest_info()
        return confirmed_cases, last_update


class RussianRegionsParser:
    """
    Getting up to date data about confirmed COVID-19 cases in Russia.
    """

    def __init__(self, cfg):
        main_cfg = cfg["rospotreb"]
        aux_cfg = cfg["auxiliary"]
        self.downloader = ReportDownloader(main_cfg)
        self.regions_fname = aux_cfg["regions"]
        self.matcher = RegionMatcher()

    def fix_date(self, df):
        df["date"] = pd.to_datetime(df.date).dt.strftime("%Y-%m-%d")
        return df

    def convert_series_format(self, original_series_df, regions_df):
        """
        Converting original files to a submission-based format.
        From regions as columns and dates as rows to the opposite.
        """
        regions_df = regions_df.set_index("csse_province_state")
        new_cols = ["date"] + list(original_series_df["Province_State"])
        date_series = (
            original_series_df[original_series_df.columns[11:]]
            .transpose()
            .reset_index()
        )
        date_series.columns = new_cols
        date_series = date_series.melt(
            id_vars=["date"], var_name="region_name", value_name="confirmed"
        )
        date_series["region"] = date_series["region_name"].apply(
            lambda x: regions_df.loc[x, "iso_code"]
        )
        return self.fix_date(date_series.set_index("region"))

    def merge_update(self, original, update):
        """
        RosPotrebNadzor updates are measured in changes by day.
        We need to add them to the originals to make resulting update cumulative.
        """
        date = datetime.strptime(update["date"][0], "%Y-%m-%d") - timedelta(days=1)
        date = date.strftime("%Y-%m-%d")
        update["region_name"] = update["region"].apply(
            lambda x: original.loc[x, "region_name"][0]
        )
        update.set_index("region", inplace=True)
        original_prev = original.query(f'date == "{date}"')
        update["confirmed"] = original_prev["confirmed"] + update["confirmed"]
        # fill missing values
        for region_code in original.index.unique():
            if region_code not in update.index:
                update.loc[region_code] = [
                    original_prev.loc[region_code, "confirmed"],
                    update["date"][0],
                    original_prev.loc[region_code, "region_name"],
                ]
        return original.append(update).sort_values(by=["region", "date"])

    def load_data(self):
        regions_df = pd.read_csv(self.regions_fname)
        # download the latest rospotrebnadzor report for up to date retrieval
        confirmed_cases, last_update = self.downloader.download_report()
        confirmed_cases = self.convert_series_format(confirmed_cases, regions_df)
        # collecting iso_alpha3 codes for raw rospotrebnadzor representations
        update = self.matcher.collect_region_update(last_update, regions_df)
        # merging the last update with data
        full_cases = self.merge_update(confirmed_cases, update)
        regions_df.set_index("iso_code", inplace=True)
        # adding proper geocodes
        full_cases = pd.merge(
            full_cases,
            regions_df["geoname_code"],
            how="outer",
            left_index=True,
            right_index=True,
        )
        full_cases.index = full_cases.index.rename("region")
        return full_cases
