from .base import ReportDownloader, fix_date


class OxfordParser:
    def __init__(self, cfg):
        self.cfg = cfg["oxford"]
        self.downloader = ReportDownloader(self.cfg)

    def _filter_columns(self, df):
        columns = [
            "CountryCode",
            "Date",
            "C1_School closing",
            "C2_Workplace closing",
            "C3_Cancel public events",
            "C4_Restrictions on gatherings",
            "C6_Stay at home requirements",
            "C7_Restrictions on internal movement",
            "C8_International travel controls",
            "E1_Income support",
            "E2_Debt/contract relief",
            "E3_Fiscal measures",
            "E4_International support",
            "H1_Public information campaigns",
            "H2_Testing policy",
            "H3_Contact tracing",
            "H4_Emergency investment in healthcare",
            "H5_Investment in vaccines",
            "StringencyIndexForDisplay",
        ]

        df = df[columns]
        df.columns = ["country_code", "date"] + [
            col.replace(" ", "_").lower() for col in df.columns[2:]
        ]
        return df

    def _process_dataframe(self, df):
        df = self._filter_columns(df)
        df = fix_date(df, "%Y%m%d")
        df = df.fillna(method="ffill")
        return df

    def load_data(self):
        raw_data = self.downloader.download_report(
            self.cfg["main_page_url"], "oxford_report.csv"
        )
        processed_data = self._process_dataframe(raw_data)
        return processed_data
