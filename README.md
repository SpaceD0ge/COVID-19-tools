# Tools for the COVID-19 information processing.
Simple up to date data retrieval tools.

[![CodeFactor](https://www.codefactor.io/repository/github/spaced0ge/covid-19-tools/badge)](https://www.codefactor.io/repository/github/spaced0ge/covid-19-tools)
[![Build Status](https://travis-ci.com/SpaceD0ge/COVID-19-tools.svg?branch=master)](https://travis-ci.com/SpaceD0ge/COVID-19-tools)

## Data sources
| Source | Description |
| --- | --- |
| [Oxford COVID-19 Government Response Tracker](https://www.bsg.ox.ac.uk/research/research-projects/oxford-covid-19-government-response-tracker) | Stringency ratings for different government responses. |
| [Google COVID-19 Community Mobility Reports](https://www.google.com/covid19/mobility/) | Mobility trends for different areas and types of places. |
| [2019-nCoV Data Repository by Johns Hopkins CSSE](https://github.com/CSSEGISandData/COVID-19/) | Tracking cases by country. |

## Requirements

python 3.5+

internet access

## Getting started

Combine all data in one dictionary with two dataframes:
```python
from data import DatasetManager
import yaml

with open('file_cfg.yml') as f:
    cfg = yaml.safe_load(f)

# to get up to date data from online sources each time
# uncomment the next part:
# cfg['reload'] = True

with open(cfg['auxiliary']['geojson']) as f:
    geodata = json.load(f)
data = DatasetManager(cfg).get_data()

assert list(data.keys()) == ['world', 'russia']
```

Or get reports separately:
```python
from data import CSSEParser, OxfordParser, GoogleParser
parsers = [
	CSSEParser(cfg),
	OxfordParser(cfg),
	GoogleParser(cfg)
]
data = [parser.load_data() for parser in parsers]
```

Train a SEIR model approximation per country:
```python
from models import CompartmentalOptimizer

optimizer = CompartmentalOptimizer(optim_days=14)
cases = [1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 7, 7, 8, 9, 10, 13]
deaths = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2]
population = 397628
result = optimizer.fit(cases, deaths, population)
```

or follow examples from the

	examples
folder

## Configuration format

The main file configuration parameters can be found in the file_cfg.yml.
Each of the main data parsers should have a root folder. Set to "./report_files" by default.
 
	root: ./report_files

Default naming convention is "iso_alpha3" (3-letter country code). The "countries.csv" file holds some additional information.

	convention: iso_alpha3
	countries: ./countries.csv

Three data sources each have their specific configuration options.

	csse: {}
	google: {}
	oxford: {}

Specify the "reload" option as true to retrieve up to date information each time.
Do not unnecessarily overload the public servers though.

	reload: false


## Running tests

	python -m pytest .

# Coming next
New data sources

Prediction models

Online dashboard
