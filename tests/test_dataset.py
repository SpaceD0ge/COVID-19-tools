import yaml
from yaml import BaseLoader
from data import DatasetManager
import pytest
import pandas as pd


@pytest.fixture(scope="class")
def config():
    print("loading config")
    with open("./file_cfg.yml") as f:
        cfg = yaml.load(f, BaseLoader)
    cfg["reload"] = True
    return cfg


@pytest.fixture(scope="class")
def country_codes_alpha3(config):
    print("loading country codes")
    data = pd.read_csv(config["auxiliary"]["countries"])
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
def world_data(dataframe):
    print("loading date level data")
    return dataframe["world"]["by_date"]


class Test_dataset:
    @pytest.mark.parametrize(
        "date, country_code, columns, values",
        [
            ("2020-03-28", "SWZ", ["c1_school_closing", "cases"], [3.0, 6.0]),
            ("2020-04-02", "USA", ["deaths", "recovered"], [7024.0, 5367.0]),
            ("2020-04-05", "RUS", ["cases", "deaths"], [4149.0, 281.0]),
        ],
    )
    def test_different_dates(self, world_data, date, country_code, columns, values):
        row = world_data[
            (world_data["date"] == date) & (world_data["country_code"] == country_code)
        ]
        assert list(row[columns].values[0]) == values

    @pytest.mark.parametrize(
        "country_code, start, end, column, changes",
        [
            (
                "DEU", "2020-03-11", "2020-03-19",
                "retail_and_recreation_percent_change_from_baseline", [0, 0, 1, 1, 0, 0, 0]
            ),
            (
                "ITA", "2020-03-09", "2020-03-17",
                "parks_percent_change_from_baseline", [0, 0, 0, 0, 0, 1, 0]
            ),
        ],
    )
    def test_graph_dynamic(self, world_data, country_code, start, end, column, changes):
        country = world_data.set_index("country_code").loc[country_code].dropna()
        mask = (country["date"] > start) & (country["date"] <= end)
        values = country[mask][column].rolling(2).apply(lambda x: x[0] < x[1])
        values = list(values[1:])
        assert values == changes

    def test_country_codes(self, world_data, country_codes_alpha3):
        codes = set(world_data["country_code"].unique())
        assert codes == country_codes_alpha3
