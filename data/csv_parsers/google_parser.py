from .base import ReportDownloader


class GoogleParser:
    def __init__(self, cfg):
        self.cfg = cfg["google"]
        self.downloader = ReportDownloader(self.cfg)

    def _filter_columns(self, df):
        df.columns = ["country_code"] + list(df.columns[1:])
        df = df[df["sub_region_1"].isna()]
        return df.drop(["country_region", "sub_region_1", "sub_region_2"], 1)

    def load_data(self):
        raw_data = self.downloader.download_report(
            self.cfg["main_page_url"], "google_report.csv"
        )
        processed_data = self._filter_columns(raw_data)
        return processed_data
