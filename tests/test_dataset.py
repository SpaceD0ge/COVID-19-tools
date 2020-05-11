import yaml
from data import DatasetManager
import pytest
import pandas as pd


@pytest.fixture(scope="class")
def config():
    with open("./file_cfg.yml") as f:
        cfg = yaml.safe_load(f)
    cfg["reload"] = True
    return cfg


@pytest.fixture(scope="class")
def country_codes_alpha3(config):
    data = pd.read_csv(config["auxiliary"]["countries"])
    data = data["iso_alpha3"].unique()
    return set(data)


@pytest.fixture(scope="class")
def manager(config):
    manager = DatasetManager(config)
    return manager


@pytest.fixture(scope="class")
def dataframe(manager):
    frame = manager.get_data()
    return frame


@pytest.fixture(scope="class")
def world_data(dataframe):
    return dataframe["world"]["by_date"]


@pytest.fixture(scope="class")
def rus_data(dataframe):
    return dataframe["russia"]["by_date"]


class Test_dataset:
    @pytest.mark.parametrize(
        "date, country_code, columns, values",
        [
            ("2020-03-28", "SWZ", ["c1_school_closing", "cases"], [3, 9]),
            ("2020-04-02", "USA", ["deaths", "cases"], [7921, 243622]),
            ("2020-04-05", "RUS", ["cases", "deaths"], [5389, 45]),
            ("2020-04-30", "RUS", ["cases", "deaths"], [106498, 1073]),
            ("2020-01-22", "AFG", ["cases", "deaths", "c1_school_closing"], [0, 0, 0]),
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

    def test_dataframe_integrity(self, dataframe):
        assert list(dataframe.keys()) == ['world', 'russia']
        world_timeline = dataframe['world']['by_date']
        for date in world_timeline['date'].unique():
            assert world_timeline[world_timeline['date'] == date].shape[0] == data['world']['by_country'].shape[0]
        rus_timeline = dataframe['russia']['by_date']
        for date in rus_timeline['date'].unique():
            assert rus_timeline[rus_timeline['date'] == date].shape[0] == data['russia']['by_region'].shape[0]
