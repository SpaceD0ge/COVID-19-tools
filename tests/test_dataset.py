import yaml
from data import DatasetManager
import pytest
import pandas as pd


@pytest.fixture(scope="class")
def config():
    print("loading config")
    with open("./file_cfg.yml") as f:
        config = yaml.load(f)
    config["reload"] = True
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
            ("2020-03-28", "SWZ", ["s1_school", "cases"], [2, 9]),
            ("2020-04-02", "USA", ["deaths", "recovered"], [5926, 9001]),
            ("2020-04-05", "RUS", ["cases", "deaths"], [5389, 45]),
        ],
    )
    def test_different_dates(self, date_data, date, country_code, columns, values):
        row = date_data[
            (date_data["date"] == date) & (date_data["country_code"] == country_code)
        ]
        assert list(row[columns].values[0]) == values

    @pytest.mark.parametrize(
        "country_code, start, end, column, changes",
        [
            ("DEU", "2020-03-11", "2020-03-19", "retail", [0, 0, 1, 1, 0, 0, 0]),
            ("ITA", "2020-03-09", "2020-03-17", "parks", [1, 0, 0, 0, 0, 1, 0]),
        ],
    )
    def test_graph_dynamic(self, date_data, country_code, start, end, column, changes):
        country = date_data.set_index("country_code").loc[country_code].dropna()
        mask = (country["date"] > start) & (country["date"] <= end)
        values = country[mask][column].rolling(2).apply(lambda x: x[0] < x[1])
        values = list(values[1:])
        assert values == changes

    def test_country_codes(self, date_data, country_codes_alpha3):
        codes = set(date_data["country_code"].unique())
        assert codes == country_codes_alpha3
