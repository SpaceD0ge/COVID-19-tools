import os
import pandas as pd
import requests


class ReportDownloader:
    def __init__(self, file_cfg):
        self.rewrite = file_cfg["rewrite"]
        self.root = file_cfg["root"]

    def download_report(self, url, to_filename):
        main_page = requests.get(url)
        if main_page.status_code != 200:
            raise ValueError(f"Wrong response code for {self.main_page_url}")
        data = main_page.content.decode()
        filename = f"{self.root}/{to_filename}"
        if not os.path.exists(filename) or self.rewrite:
            with open(filename, "w") as f:
                f.write(data)

        dataframe = pd.read_csv(filename)
        return dataframe


def fix_date(df, date_format=None):
    df["date"] = pd.to_datetime(df.date, format=date_format).dt.strftime("%Y-%m-%d")
    return df
