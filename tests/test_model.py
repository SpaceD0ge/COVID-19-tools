from data import DatasetManager
from models import CompartmentalOptimizer
from models.selection import model_per_country_simple_split
import pandas as pd
import pytest
import yaml


@pytest.fixture(scope="class")
def config():
    print("loading config")
    with open("./file_cfg.yml") as f:
        config = yaml.load(f)
    return config


@pytest.fixture(scope="class")
def manager(config):
    print("loading manager")
    manager = DatasetManager(config)
    return manager


@pytest.fixture(scope="class")
def date_data(manager):
    print("loading date dataframe")
    frames = manager.get_data()
    frame = frames["by_date"].set_index("country_code")
    return frame


@pytest.fixture(scope="class")
def population(manager):
    print("loading country dataframe")
    frames = manager.get_data()
    frame = frames["by_country"].set_index("country_code")["population"]
    return frame


@pytest.fixture(scope="class")
def optimizer(manager):
    print("loading optimizer")
    return CompartmentalOptimizer(optim_days=14)


class Test_model:
    @pytest.mark.parametrize(
        "country_code, start, end, result, r_0",
        [
            ("DEU", "2020-01-27", "2020-04-11", 0.001577, 3.7513),
            ("RUS", "2020-01-31", "2020-04-11", 0.028109, 3.7446),
        ],
    )
    def test_compartment_with_dataframe(
        self, optimizer, date_data, population, country_code, start, end, result, r_0
    ):
        country = date_data.loc[country_code]
        mask = (country["date"] >= start) & (country["date"] <= end)
        cases = country[mask]["cases"].values
        deaths = country[mask]["deaths"].values
        pop = population[country_code]

        res = optimizer.fit(cases, deaths, pop)
        pred_cases, pred_dead = optimizer.predict(res.x, cases, deaths, pop, 30)
        assert len(cases) == len(deaths)
        assert len(pred_cases) == len(pred_dead)
        assert len(cases) + 30 == len(pred_cases)
        assert round(res.fun, 6) == result
        assert round(res.x[0], 4) == r_0

    @pytest.mark.parametrize(
        "cases, deaths, pop, result, r_0",
        [
            (
                [1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 7, 7, 8, 9, 10, 13],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2],
                397628,
                0.036675,
                1.9216,
            ),
        ],
    )
    def test_compartment_raw(self, optimizer, cases, deaths, pop, result, r_0):
        res = optimizer.fit(cases, deaths, pop)
        pred_cases, pred_dead = optimizer.predict(res.x, cases, deaths, pop, 30)
        assert round(res.fun, 6) == result
        assert round(res.x[0], 4) == r_0

    def test_splits(self, date_data):
        codes = set(date_data.index.unique())
        splits = model_per_country_simple_split(date_data, targets=["cases", "deaths"])
        country_codes_alpha3 = set([x for x, y in splits])
        assert codes == country_codes_alpha3
