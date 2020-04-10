from .google_mobility_report import CountryReportParser
from .oxford import OxfordParser
from .csse import CSSEParser
import pandas as pd
import os


class Convention:
    def __init__(self, country_code_file, convention_code="iso_alpha3"):
        self.convention = convention_code
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
        return report


class DateLevelStatCollector:
    def __init__(self, cfg):
        self.convention = Convention(cfg["countries"], cfg["convention"])
        csse_parser = CSSEParser(cfg["csse"])
        google_parser = CountryReportParser(cfg["google"])
        oxford_parser = OxfordParser(cfg["oxford"])
        self.parsers = [csse_parser, google_parser, oxford_parser]

    def collect_dataframe(self):
        reports = [parser.load_data() for parser in self.parsers]
        reports = [self.convention.fix_report(report) for report in reports]

        joint_report = None
        for report_index in range(len(reports) - 1):
            left_report = (
                reports[report_index].dropna() if joint_report is None else joint_report
            )
            right_report = reports[report_index + 1]

            joint_report = pd.merge(
                left_report,
                right_report.dropna(),
                how="left",
                left_on=["date", "country_code"],
                right_on=["date", "country_code"],
            )

        return joint_report


class CountryLevelStatCollector:
    def __init__(self, cfg):
        self.country_file = cfg["countries"]
        self.convention = cfg["convention"]

    def collect_dataframe(self):
        data = pd.read_csv(self.country_file)
        new_columns = [self.convention] + list(data.columns)[6:]
        return data[new_columns].rename(columns={"iso_alpha3": "country_code"})


class DatasetManager:
    def __init__(self, cfg):
        self.root = cfg["root"]
        self.reload = cfg["reload"]
        self.country_parser = CountryLevelStatCollector(cfg)
        self.date_parser = DateLevelStatCollector(cfg)

    def _load(self, filename, parser):
        if os.path.exists(filename) and self.reload is False:
            dataframe = pd.read_csv(filename)
        else:
            dataframe = parser.collect_dataframe()
            dataframe.to_csv(filename)
        return dataframe

    def get_data(self):
        return {
            "by_country": self._load(
                f"{self.root}/country_level_data.csv", self.country_parser
            ),
            "by_date": self._load(
                f"{self.root}/date_level_data.csv", self.date_parser
            ),
        }
