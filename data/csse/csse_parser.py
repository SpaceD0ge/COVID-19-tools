from datetime import datetime
import pandas as pd
import requests
import numpy as np
import os


class ReportDownloader:
    def __init__(self, file_cfg):
        self.cfg = file_cfg

    def _download_report(self, link):
        paige = requests.get(link)
        if paige.status_code != 200:
            raise ValueError(f"Wrong response code for {link}")
        data = paige.content.decode()
        filename = self.cfg["root"] + "/" + link.split("/")[-1]
        if not os.path.exists(filename) or self.cfg["rewrite"]:
            with open(filename, "w") as f:
                f.write(data)
        dataframe = pd.read_csv(filename)
        return dataframe.drop(["Lat", "Long"], 1)

    def load_files(self):
        frames = [
            self._download_report(self.cfg["global_confirmed"]),
            self._download_report(self.cfg["global_deaths"]),
            self._download_report(self.cfg["global_recovered"]),
        ]

        return frames


class CSSEParser:
    def __init__(self, file_cfg):
        self.downloader = ReportDownloader(file_cfg)

    def _compose(self, frames):
        frames = [frame.groupby("Country/Region").sum() for frame in frames]
        assert frames[0].shape == frames[1].shape == frames[2].shape
        raw_data = np.stack([frame.values for frame in frames], -1)
        return frames[0].index, frames[0].columns, raw_data

    def _fix_date(self, date_string):
        date = datetime.strptime(date_string, "%m/%d/%y")
        return date.strftime("%Y-%m-%d")

    def load_data(self):
        frames = self.downloader.load_files()
        countries, dates, values = self._compose(frames)

        csv_data = []
        for country_idx, country_name in enumerate(countries):
            for date_idx, date in enumerate(dates):
                csv_data.append(
                    [date, country_name] + list(values[country_idx][date_idx])
                )
        csv_data = pd.DataFrame(
            csv_data, columns=["date", "country_code", "cases", "deaths", "recovered"]
        )
        csv_data.loc[:, "date"] = csv_data["date"].apply(lambda x: self._fix_date(x))
        return csv_data
