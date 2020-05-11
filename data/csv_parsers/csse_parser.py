import pandas as pd
from .base import ReportDownloader, fix_date


class CSSEParser:
    def __init__(self, cfg):
        self.cfg = cfg["csse"]
        self.downloader = ReportDownloader(self.cfg)
        self.data = [
            (self.cfg["global_confirmed"], "world_timeseries_confirmed.csv"),
            (self.cfg["global_deaths"], "world_timeseries_deaths.csv"),
        ]

    def _compose(self, frames):
        frames = [frame.groupby("Country/Region").sum() for frame in frames]
        frames = [
            pd.melt(
                frame.drop(["Lat", "Long"], 1).reset_index(),
                id_vars=["Country/Region"],
                var_name="date",
                value_name="val",
            ).set_index(["Country/Region", "date"])
            for frame in frames
        ]
        frames = pd.concat(frames, axis=1).reset_index()
        return frames

    def load_data(self):
        frames = [
            self.downloader.download_report(page, fname) for page, fname in self.data
        ]
        frames = self._compose(frames)
        frames.columns = ["country_code", "date", "cases", "deaths"]
        csv_data = fix_date(frames, "%m/%d/%y").sort_values(by=["country_code", "date"])
        return csv_data
