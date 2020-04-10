from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests
import fitz
import re
import os


class XrefStreamParser:
    """
    Modified version of
    https://gist.github.com/Amarang/3341c9a24da4556def7c3a03a12949b8
    """

    def __init__(self):
        pass

    def _parse_stream(self, stream):
        data_raw = []
        data_transformed = []
        for line in stream.splitlines():
            if line.endswith(" cm"):
                rotparams = list(map(float, line.split()[:-1]))
            elif line.endswith(" l"):
                x, y = list(map(float, line.split()[:2]))
                a, b, c, d, e, f = rotparams
                xp = a * x + c * y + e
                yp = b * x + d * y + f
                data_transformed.append([xp, yp])
                data_raw.append([x, y])
            else:
                pass
        return np.array(data_raw)

    def _process_coordinates(self, raw_data):
        basex, basey = raw_data[-1]
        if basex == 0.0:
            data = basey - raw_data[:, 1]
            data = np.trim_zeros(data, "f")
        else:
            data = raw_data[:, 1]
        return data[::-1]

    def parse_xref(self, xref):
        raw_data = self._parse_stream(xref)
        coordinates = self._process_coordinates(raw_data)
        return np.array(coordinates)

    def __call__(self, xref):
        return self.parse_xref(xref)


class CoordinateParser:
    """
    Coordinate parser for proper coordinate extraction.
    Each graph can end up being incomplete or broken. CoordinateParser evens
    out each sequences shape and fills missing data with np.nan.
    """

    def __init__(self):
        self.xref_parser = XrefStreamParser()

    def _fix_coordinates(self, coordinates):
        coordinate_range = len(coordinates[0])
        for index in range(1, len(coordinates)):
            if coordinates[index][0] != 0 or len(coordinates[index]) > coordinate_range:
                coordinates[index] = [np.nan for _ in range(coordinate_range)]
            elif len(coordinates[index]) < coordinate_range:
                coordinates[index] = np.concatenate(
                    [
                        coordinates[index],
                        [
                            np.nan
                            for _ in range(coordinate_range - len(coordinates[index]))
                        ],
                    ]
                )
        return coordinates

    def _collect_raw_coordinates(self, doc):
        """
        Collecting raw coordinate points from pdf xref streams
        through the XrefStreamParser class functions.
        """
        coordinates = []
        for page_index in range(2):
            xrefs = sorted(
                doc.getPageXObjectList(page_index),
                key=lambda x: int(x[1].replace("X", "")),
            )
            for xref in xrefs:
                stream = doc.xrefStream(xref[0]).decode()
                raw_graph_points = self.xref_parser(stream)
                coordinates.append(raw_graph_points)
        coordinates = self._fix_coordinates(coordinates)
        return coordinates

    def _get_reference_points(self, doc):
        """
        Reading reference points to fix the XrefStreamParser output.
        Simple stream parsing procedures return skewed data. We need
        to center it around reference points found in text.
        """
        references = []
        for page_index in range(2):
            sentences = doc.getPageText(page_index).split("\n")
            for sentence_index in range(1, len(sentences) - 1):
                if sentences[sentence_index + 1] == "compared to baseline":
                    if sentences[sentence_index] == "Not enough data for this date":
                        return None
                    percentage_text = sentences[sentence_index]
                    percentage_value = int(percentage_text[:-1])
                    references.append(percentage_value)
        return references

    def get_graph_coordinates(self, doc):
        coordinates = self._collect_raw_coordinates(doc)
        references = self._get_reference_points(doc)
        if references is None:
            return None
        assert len(coordinates) == len(references)
        for index in range(len(coordinates)):
            nan_mask = ~np.isnan(coordinates[index])
            if True in nan_mask:
                coordinates[index][nan_mask] *= abs(
                    references[index] / coordinates[index][nan_mask][-1]
                )
        return coordinates


class DocumentParser:
    """
    Reads a pdf file by its filepath to stream the contents into a
    readable coordinate format.
    """

    def __init__(self, convention="alpha2"):
        self.convention = convention
        self.coordinate_parser = CoordinateParser()

    def _get_country_name(self, doc, country_code):
        """
        Different codes do not necessarily match between different systems.
        Retreiving specific country denomination instead.
        """
        if self.convention == "name" or country_code is None:
            title = doc.getPageText(0).split("\n")[1]
            name_parts = title.split()
            name = " ".join(name_parts[:-3])
        elif self.convention == "alpha2":
            name = country_code
        else:
            raise ValueError(f"Wrong naming convention format {self.convention}")
        return name

    def parse_document(self, filepath, country_code=None):
        """
        Collecting graphs from a single pdf report document.
        Every country level document follows the same template of two pages 
        with the six statistic graphs in the same order.
        Returns a tuple of (name, list of six np.arrays)
        """
        document = fitz.Document(filepath)
        name = self._get_country_name(document, country_code)
        coordinates = self.coordinate_parser.get_graph_coordinates(document)
        return name, coordinates

    def __call__(self, filepath, country_code=None):
        return self.parse_document(filepath, country_code)


class ReportDownloader:
    """
    Downloads the main country list from the latest Google report.
    Processes every code to corresponding pdf file.
    """

    def __init__(self, date, file_cfg, country_codes=None):
        self.date = date
        self.root = file_cfg["root"]
        self.main_page_url = file_cfg["main_page_url"]
        self.link_start = file_cfg["link_start"]
        self.link_end = file_cfg["link_end"]
        self.rewrite = file_cfg["rewrite"]
        if country_codes is None or date == "latest" or date is None:
            self.date, self.codes = self._load_country_codes()

    def _load_country_codes(self):
        """
        Reads the main country list from the main Google report page.
        Returns a tuple of (latest_date, codes)
        """
        main_paige = requests.get(self.main_page_url)
        if main_paige.status_code != 200:
            raise ValueError(f"Wrong response code for {self.main_page_url}")
        code_pattern = "[A-Z]{2}"
        date_pattern = "[0-9]{4}-[0-9]{2}-[0-9]{2}"
        reports = set(
            re.findall(
                f"{self.link_start}{date_pattern}_{code_pattern}{self.link_end}",
                main_paige.content.decode(),
            )
        )
        # 10 characters for a date string of format 1234-56-78
        # and one to an underscore
        prefix_len = len(self.link_start) + 11
        codes = [report[prefix_len : prefix_len + 2] for report in reports]
        last_date = list(reports)[0][len(self.link_start) : len(self.link_start) + 10]
        return last_date, sorted(codes)

    def _get_link(self, country_code):
        return f"{self.link_start}{self.date}_{country_code}{self.link_end}"

    def _download_report(self, country_code):
        filename = f"{self.root}/{country_code}_report.pdf"
        if not os.path.exists(filename) or self.rewrite:
            url = self._get_link(country_code)
            response = requests.get(url)
            if response.status_code != 200:
                raise ValueError(f"Wrong response code for {url}")
            with open(filename, "wb") as f:
                f.write(response.content)
        return filename

    def process_country_list(self, country_list=None):
        """
        Output: dictionary of strings {code: path}.
        """
        if country_list is None:
            country_list = self.codes
            if self.codes is None:
                raise ValueError("Wrong country code list")
        return {
            country_code: self._download_report(country_code)
            for country_code in country_list
        }


class CountryReportParser:
    """
    Collects reports for a comma-separated file format conversion.
    Returns a pandas DataFrame object.
    """

    def __init__(self, file_cfg, date="latest", convention="alpha2"):
        self.downloader = ReportDownloader(date, file_cfg)
        self.document_parser = DocumentParser(convention)
        self.graph_names = [
            "date",
            "country_code",
            "retail",
            "grocery",
            "parks",
            "transit",
            "work",
            "residential",
        ]

    def _collect_reports(self, country_codes):
        report_files = self.downloader.process_country_list(country_codes)
        report_data = [
            self.document_parser(report, code) for code, report in report_files.items()
        ]
        graphs = dict(report_data)
        return graphs

    def _to_dataframe(self, data):
        return pd.DataFrame(data, columns=self.graph_names)

    def load_data(self, country_codes=None):
        reports = self._collect_reports(country_codes)
        last_day = datetime.strptime(self.downloader.date, "%Y-%m-%d")
        csv_data = []
        for key in reports:
            if reports[key] is None:
                continue
            time_period = len(reports[key][0])
            for day_delta in range(time_period):
                current_day = last_day - timedelta(days=day_delta)
                time_str = current_day.strftime("%Y-%m-%d")
                info = [time_str, key]
                values = [
                    reports[key][graph_idx][-day_delta - 1] for graph_idx in range(6)
                ]
                info.extend(values)
                csv_data.append(info)
        return self._to_dataframe(csv_data)
