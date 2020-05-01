from .csv_parsers import OxfordParser, CSSEParser, GoogleParser
from .rospotrebnadzor import RussianRegionsParser
import pandas as pd
import os


class Convention:
    def __init__(self, cfg):
        country_code_file = cfg["countries"]
        self.convention = cfg["convention"]
        conventions = set(
            [
                "iso_alpha2",
                "iso_alpha3",
                "iso_numeric",
                "name",
                "official_name",
                "ccse_name",
            ]
        )
        self.converters = {
            code: pd.read_csv(country_code_file, index_col=code).to_dict()
            for code in conventions
            if code != self.convention
        }

    def _get_country_convention(self, country_code):
        if country_code.isupper():
            if len(country_code) == 2:
                return "iso_alpha2"
            elif len(country_code) == 3:
                return "iso_alpha3"
            else:
                raise ValueError(f"Can't find proper convention for {country_code}")
        else:
            return "ccse_name"

    def _convert_code(self, code, from_convention):
        converter = self.converters[from_convention]
        if code in converter[self.convention]:
            return converter[self.convention][code]
        return None

    def fix_report(self, report, key="country_code"):
        report_convention = self._get_country_convention(report.loc[0, key])
        if report_convention != self.convention:
            report.loc[:, key] = report[key].apply(
                lambda x: self._convert_code(x, report_convention)
            )
        return report[report[key].notna()]


class DateLevelStatCollector:
    def __init__(self, cfg):
        self.convention = Convention(cfg["auxiliary"])
        csse_parser = CSSEParser(cfg)
        oxford_parser = OxfordParser(cfg)
        google_parser = GoogleParser(cfg)
        self.parsers = [csse_parser, oxford_parser, google_parser]

    def collect_dataframe(self):
        reports = [parser.load_data() for parser in self.parsers]
        reports = [
            self.convention.fix_report(report, "country_code") for report in reports
        ]

        joint_report = None
        for report_index in range(len(reports) - 1):
            left_report = (
                reports[report_index] if joint_report is None else joint_report
            )
            right_report = reports[report_index + 1]

            joint_report = pd.merge(
                left_report,
                right_report,
                how="left",
                left_on=["date", "country_code"],
                right_on=["date", "country_code"],
            )

        return joint_report


class SummaryStatCollector:
    def __init__(self, cfg):
        self.cfg = cfg["auxiliary"]

    def collect_dataframe(self, key="countries"):
        country_file = self.cfg[key]
        data = pd.read_csv(country_file)
        return data.rename(columns={"iso_alpha3": "country_code"})


class RegionLevelStatCollector:
    def __init__(self, cfg):
        self.rosparser = RussianRegionsParser(cfg)

    def collect_dataframe(self):
        report = self.rosparser.load_data()
        return report.reset_index()


class DatasetManager:
    def __init__(self, cfg):
        self.root = cfg["root"]
        self.reload = cfg["reload"]
        self.summary = SummaryStatCollector(cfg)
        self.date_parser = DateLevelStatCollector(cfg)
        self.region_parser = RegionLevelStatCollector(cfg)

    def _load(self, filename, parser, **args):
        if os.path.exists(filename) and self.reload is False:
            dataframe = pd.read_csv(filename)
        else:
            dataframe = parser.collect_dataframe(**args)
            dataframe.to_csv(filename, index=False)
        return dataframe

    def get_data(self):
        wold_countries = self._load(
            f"{self.root}/world_countries.csv", self.summary, key="countries"
        )
        world_timeseries = self._load(
            f"{self.root}/world_confirmed_cases.csv", self.date_parser
        )
        russia_regions = self._load(
            f"{self.root}/rus_regions.csv", self.summary, key="regions"
        )
        russia_timeseries = self._load(
            f"{self.root}/rus_confirmed_cases.csv", self.region_parser
        )

        return {
            "world": {"by_country": wold_countries, "by_date": world_timeseries},
            "russia": {"by_region": russia_regions, "by_date": russia_timeseries},
        }
