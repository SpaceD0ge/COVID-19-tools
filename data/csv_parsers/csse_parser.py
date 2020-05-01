import pandas as pd
import numpy as np
from .base import ReportDownloader, fix_date


class CSSEParser:
    def __init__(self, cfg):
        self.cfg = cfg["csse"]
        self.downloader = ReportDownloader(self.cfg)
        self.data = [
            (self.cfg["global_confirmed"], "world_timeseries_confirmed.csv"),
            (self.cfg["global_recovered"], "world_timeseries_recovered.csv"),
            (self.cfg["global_deaths"], "world_timeseries_deaths.csv"),
        ]

    def _compose(self, frames):
        frames = [frame.groupby("Country/Region").sum() for frame in frames]
        assert frames[0].shape == frames[1].shape == frames[2].shape
        raw_data = np.stack([frame.values for frame in frames], -1)
        return frames[0].index, frames[0].columns[2:], raw_data

    def load_data(self):
        frames = [
            self.downloader.download_report(page, fname) for page, fname in self.data
        ]
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
        csv_data = fix_date(csv_data, "%m/%d/%y")
        return csv_data
