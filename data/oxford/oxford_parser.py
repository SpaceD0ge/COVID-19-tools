import os
import pandas as pd
import requests


class ReportDownloader:
    def __init__(self, file_cfg):
        self.main_page_url = file_cfg["main_page_url"]
        self.rewrite = file_cfg["rewrite"]
        self.root = file_cfg["root"]

    def download_report(self):
        main_paige = requests.get(self.main_page_url)
        if main_paige.status_code != 200:
            raise ValueError(f"Wrong response code for {self.main_page_url}")
        data = main_paige.content.decode()
        filename = f"{self.root}/oxford_report.csv"
        if not os.path.exists(filename) or self.rewrite:
            with open(filename, "w") as f:
                f.write(data)

        dataframe = pd.read_csv(filename)
        return dataframe


class OxfordParser:
    def __init__(self, file_cfg):
        self.downloader = ReportDownloader(file_cfg)

    def _filter_columns(self, df):
        columns = [
            "CountryCode",
            "Date",
            "S1_School closing",
            "S2_Workplace closing",
            "S3_Cancel public events",
            "S4_Close public transport",
            "S5_Public information campaigns",
            "S6_Restrictions on internal movement",
            "S7_International travel controls",
            "S8_Fiscal measures",
            "S9_Monetary measures",
            "S10_Emergency investment in health care",
            "StringencyIndexForDisplay",
        ]
        df = df[columns]
        df.columns = [
            "country_code",
            "date",
            "s1_school",
            "s2_workplace",
            "s3_events",
            "s4_transport",
            "s5_info",
            "s6_movement",
            "s7_travel",
            "s8_fiscal",
            "s9_monetary",
            "s10_investment",
            "stringency",
        ]
        return df

    def _fix_date(self, df):
        df.loc[:, "date"] = df["date"].apply(lambda x: str(x))
        df.loc[:, "date"] = df["date"].apply(lambda x: f"{x[:4]}-{x[4:6]}-{x[6:]}")
        return df

    def _process_dataframe(self, df):
        df = self._filter_columns(df)
        df = self._fix_date(df)
        df = df.fillna(method="ffill")
        return df

    def load_data(self):
        raw_data = self.downloader.download_report()
        processed_data = self._process_dataframe(raw_data)
        return processed_data
