import yaml
from data import DatasetManager
import pytest
import pandas as pd


@pytest.fixture(scope="class")
def config():
    print("loading config")
    with open("./file_cfg.yml") as f:
        config = yaml.load(f)
    return config


@pytest.fixture(scope="class")
def country_codes_alpha3(config):
    print("loading country codes")
    data = pd.read_csv(config["countries"])
    data = data["iso_alpha3"].unique()
    return set(data)


@pytest.fixture(scope="class")
def manager(config):
    print("loading manager")
    manager = DatasetManager(config)
    return manager


@pytest.fixture(scope="class")
def dataframe(manager):
    print("loading dataframe")
    frame = manager.get_data()
    return frame


@pytest.fixture(scope="class")
def date_data(dataframe):
    print("loading date level data")
    return dataframe["by_date"]


class Test_dataset:
    @pytest.mark.parametrize(
        "date, country_code, columns, values",
        [
            (
                "2020-03-28",
                "SWZ",
                ["stringency", "s1_school", "cases"],
                [50.0, 2.0, 9.0],
            ),
            (
                "2020-04-02",
                "USA",
                ["stringency", "deaths", "recovered"],
                [66.67, 5926.0, 9001.0],
            ),
            ("2020-04-05", "RUS", ["cases", "deaths"], [5389, 45]),
            (
                "2020-04-05",
                "AGO",
                ["retail", "grocery", "parks", "transit", "work"],
                [-62.0, -37.0, -48.0, -63.00000000000001, -17.0],
            ),
        ],
    )
    def test_different_dates(self, date_data, date, country_code, columns, values):
        row = date_data[
            (date_data["date"] == date) & (date_data["country_code"] == country_code)
        ]
        assert list(row[columns].values[0]) == values

    def test_countries(self, date_data, country_codes_alpha3):
        codes = set(date_data["country_code"].unique())
        assert codes == country_codes_alpha3
