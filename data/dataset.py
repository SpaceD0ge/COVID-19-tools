from .oxford import OxfordParser
from .csse import CSSEParser
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

    def fix_report(self, report):
        report_convention = self._get_country_convention(report.loc[0, "country_code"])
        if report_convention != self.convention:
            report.loc[:, "country_code"] = report["country_code"].apply(
                lambda x: self._convert_code(x, report_convention)
            )
        return report[report["country_code"].notna()]


class DateLevelStatCollector:
    def __init__(self, cfg):
        self.convention = Convention(cfg["auxiliary"])
        csse_parser = CSSEParser(cfg["csse"])
        oxford_parser = OxfordParser(cfg["oxford"])
        self.parsers = [csse_parser, oxford_parser]

    def collect_dataframe(self):
        reports = [parser.load_data() for parser in self.parsers]
        reports = [self.convention.fix_report(report) for report in reports]

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


class CountryLevelStatCollector:
    def __init__(self, cfg):
        self.country_file = cfg["auxiliary"]["countries"]
        self.convention = cfg["auxiliary"]["convention"]

    def collect_dataframe(self):
        data = pd.read_csv(self.country_file)
        new_columns = [self.convention] + list(data.columns)[6:]
        return data[new_columns].rename(columns={"iso_alpha3": "country_code"})


class RegionLevelStatCollector:
    def __init__(self, cfg):
        self.rosparser = RussianRegionsParser(cfg["rospotreb"], cfg["auxiliary"])
        self.report = None

    def preload(self):
        if self.report is None:
            self.report, self.updated_region_data = self.rosparser.load_data()

    def collect_dataframe(self, part_id):
        self.preload()
        if part_id == "timeseries":
            return self.updated_region_data
        return self.report


class DatasetManager:
    def __init__(self, cfg):
        self.root = cfg["root"]
        self.reload = cfg["reload"]
        self.country_parser = CountryLevelStatCollector(cfg)
        self.date_parser = DateLevelStatCollector(cfg)
        self.region_parser = RegionLevelStatCollector(cfg)

    def _load(self, filename, parser, **args):
        if os.path.exists(filename) and self.reload is False:
            dataframe = pd.read_csv(filename, index_col=0)
        else:
            dataframe = parser.collect_dataframe(**args)
            dataframe.to_csv(filename)
        return dataframe

    def get_data(self):
        wold_countries = self._load(
            f"{self.root}/country_level_data.csv", self.country_parser
        )
        world_timeseries = self._load(
            f"{self.root}/date_level_data.csv", self.date_parser
        )
        russia_regions = self._load(
            f"{self.root}/rus_regions.csv", self.region_parser, part_id="timeseries"
        )
        russia_timeseries = self._load(
            f"{self.root}/rus_confirmed_cases.csv", self.region_parser, part_id="info"
        )

        return {
            "world": {"by_country": wold_countries, "by_date": world_timeseries},
            "russia": {"by_region": russia_regions, "by_date": russia_timeseries},
        }
