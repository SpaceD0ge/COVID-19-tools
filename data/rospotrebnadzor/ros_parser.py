import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import requests
import pandas as pd
import numpy as np
import re


class GeoJsonRus:
    """
    Loading Russian regions geographical polygons with corresponding
    area codes, fixing wrong geoname_codes in the original 
    "russia_regions" file.
    """

    def __init__(self, fname):
        with open(fname) as f:
            geodata = json.load(f)
        self.geodata = geodata

    def get_region_codes(self, regions_df):
        df = regions_df.reset_index().set_index("csse_province_state")
        codes = [
            (x["properties"]["HASC_1"], x["properties"]["NL_NAME_1"])
            for x in self.geodata["features"]
        ]
        codes = sorted(
            codes,
            key=lambda x: x[1]
            .lower()
            .replace("e", "е")
            .replace("у́", "у")
            .replace("республика ", ""),
        )
        iso = (
            df.drop(["Sevastopol", "Republic of Crimea"])[["name"]]
            .sort_values("name")
            .index
        )
        codes = dict(zip([x for x in iso], [x[0] for x in codes]))
        return codes

    def fix_regions(self, regions_df):
        df = regions_df.set_index("iso_code")
        df.loc[["RU-NEN", "RU-AL", "RU-CHU"], "csse_province_state"] = [
            "Nenetskiy autonomous oblast",
            "Altay republic",
            "Chukotskiy autonomous oblast",
        ]
        codes = self.get_region_codes(df)
        df["geoname_code"] = df["csse_province_state"].apply(
            lambda x: codes[x] if x in codes else None
        )
        return df.reset_index()


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
        matches = [(x[0][0].lower(), int(x[0][1])) for x in matches if len(x) == 1]
        matches = [(self.get_simplified_region(x[0]), x[1]) for x in matches]
        iso_codes = region_df.set_index("name")["iso_code"].to_dict()
        iso_codes = {self.get_simplified_region(x): iso_codes[x] for x in iso_codes}
        matched_codes = [(iso_codes[x[0]], x[1]) for x in matches]
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

    def download(self):
        confirmed_cases = pd.read_csv(self.cfg["timeseries_page"])
        last_update = self.get_latest_info()
        return confirmed_cases, last_update


class RussianRegionsParser:
    """
    Getting up to date data about confirmed COVID-19 cases in Russia.
    """

    def __init__(self, cfg, aux_cfg):
        self.downloader = ReportDownloader(cfg)
        self.matcher = RegionMatcher()
        self.geo = GeoJsonRus(aux_cfg["geojson"])
        self.regions_fn = aux_cfg["regions"]

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
        update["confirmed"] = (
            original_prev["confirmed"] + update["confirmed"]
        )
        # fill missing values
        for region_code in original.index.unique():
            if region_code not in update.index:
                update.loc[region_code] = [
                    original_prev.loc[region_code, 'confirmed'],
                    update["date"][0],
                    original_prev.loc[region_code, 'region_name']
                ]
        return original.append(update).sort_values(by=["region", "date"])

    def load_data(self):
        # fix wrong region format
        regions_df = pd.read_csv(self.regions_fn)
        regions_df = self.geo.fix_regions(regions_df)
        # download the latest rospotrebnadzor report for up to date retrieval
        confirmed_cases, last_update = self.downloader.download()
        confirmed_cases = self.convert_series_format(confirmed_cases, regions_df)
        # collecting iso_alpha3 codes for raw rospotrebnadzor representations
        update = self.matcher.collect_region_update(last_update, regions_df)
        # merging the last update with data
        full_cases = self.merge_update(confirmed_cases, update)
        regions_df.set_index("iso_code", inplace=True)
        # adding proper geocodes
        full_cases = pd.merge(
            full_cases, regions_df["geoname_code"], how='outer', left_index=True, right_index=True
        )
        full_cases.index = full_cases.index.rename("region")
        return full_cases, regions_df
