from data import DatasetManager
from models import CompartmentalOptimizer
from models.selection import model_per_country_simple_split
import pytest
import yaml


@pytest.fixture(scope="class")
def config():
    with open("./file_cfg.yml") as f:
        cfg = yaml.safe_load(f)
    return cfg


@pytest.fixture(scope="class")
def manager(config):
    manager = DatasetManager(config)
    return manager


@pytest.fixture(scope="class")
def world_data(manager):
    frames = manager.get_data()
    frame = frames["world"]["by_date"].set_index("country_code")
    return frame


@pytest.fixture(scope="class")
def population(manager):
    frames = manager.get_data()
    frame = frames["world"]["by_country"].set_index("country_code")["population"]
    return frame


@pytest.fixture(scope="class")
def optimizer(manager):
    return CompartmentalOptimizer(optim_days=14)


class Test_model:
    @pytest.mark.parametrize(
        "country_code, start, end, result, r_0",
        [
            ("DEU", "2020-02-14", "2020-04-11", 0.008, 3.1407),
            ("RUS", "2020-02-14", "2020-04-11", 0.08, 6.9888),
        ],
    )
    def test_compartment_with_dataframe(
        self, optimizer, world_data, population, country_code, start, end, result, r_0
    ):
        country = world_data.loc[country_code]
        mask = (country["date"] >= start) & (country["date"] <= end)
        cases = country[mask]["cases"].values
        deaths = country[mask]["deaths"].values
        pop = population[country_code]

        res = optimizer.fit(cases, deaths, pop)
        pred_cases, pred_dead = optimizer.predict(res.x, cases, deaths, pop, 30)
        assert len(cases) == len(deaths)
        assert len(pred_cases) == len(pred_dead)
        assert len(cases) + 30 == len(pred_cases)
        assert round(res.fun, 6) < result
        assert round(res.x[0], 4) == r_0

    @pytest.mark.parametrize(
        "cases, deaths, pop, result, r_0",
        [
            (
                [1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 7, 7, 8, 9, 10, 13],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2],
                397628,
                0.01,
                3.4888,
            ),
        ],
    )
    def test_compartment_raw(self, optimizer, cases, deaths, pop, result, r_0):
        res = optimizer.fit(cases, deaths, pop)
        pred_cases, pred_dead = optimizer.predict(res.x, cases, deaths, pop, 30)
        assert round(res.fun, 6) < result
        assert round(res.x[0], 4) == r_0

    def test_splits(self, world_data):
        codes = set(world_data.index.unique())
        splits = model_per_country_simple_split(world_data, targets=["cases", "deaths"])
        country_codes_alpha3 = {x for x, y in splits}
        assert codes == country_codes_alpha3
