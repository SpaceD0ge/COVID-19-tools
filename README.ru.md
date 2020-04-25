# Инструменты для обработки информации о COVID-19.

[![CodeFactor](https://www.codefactor.io/repository/github/spaced0ge/covid-19-tools/badge)](https://www.codefactor.io/repository/github/spaced0ge/covid-19-tools)
[![Build Status](https://travis-ci.com/SpaceD0ge/COVID-19-tools.svg?branch=master)](https://travis-ci.com/SpaceD0ge/COVID-19-tools)

## Источники данных
| Source | Description |
| --- | --- |
| [Oxford COVID-19 Government Response Tracker](https://www.bsg.ox.ac.uk/research/research-projects/oxford-covid-19-government-response-tracker) | Реакция правительств стран, размеченная по шкале с индексом "строгости"|
| [Google COVID-19 Community Mobility Reports](https://www.google.com/covid19/mobility/) | графики изменения посещаемости розницы, аптек, парков и т.д. по странам. |
| [2019-nCoV Data Repository by Johns Hopkins CSSE](https://github.com/CSSEGISandData/COVID-19/) | Число подтвержденных заболеваний/смертей. |

## Требования

python 3.5+

доступ в интернет

## С чего начать

Собрать все данные в словарь из двух pandas.DataFrame:
```python
from data import DatasetManager
import yaml

with open('file_cfg.yml') as f:
    cfg = yaml.load(f)

# чтобы собрать свежие данные, нужно раскомментировать
# следующую строку:
# cfg['reload'] = True

data = DatasetManager(cfg).get_data()
assert(list(data.keys()) == ['world', 'russia'])
```

Или получить отчеты отдельно:
```python
from data import CSSEParser, OxfordParser, RussianRegionsParser
parsers = [
	CSSEParser(cfg['csse']),
	OxfordParser(cfg['oxford']),
	RussianRegionsParser(cfg[rospotreb], cfg['auxiliary'])
]
data = [parser.load_data() for parser in parsers]
```

Оптимизировать SEIR модель по данным страны:
```python
from models import CompartmentalOptimizer

optimizer = CompartmentalOptimizer(optim_days=14)
result = optimizer.fit(cases, deaths, population)
```
или следуя примерам из папки

	examples

## Формат файла конфигурации

Основные параметры системы работы с файлами собраны в file_cfg.yml.
Каждый парсер отчетов должен сохранять свои файлы в свою папку root. Установлена в "./report_files" по умолчанию.
 
	root: ./report_files

Коды стран взяты из схемы "iso_alpha3" (3-буквенной). Файл "countries.csv" содержит не меняющуюся со временем
информацию по странам.

	convention: iso_alpha3
	countries: ./countries.csv

У каждого из источников свои конфигурации.

	csse: {}
	google: {}
	oxford: {}

Для того, чтобы каждый раз получать новую информацию, нужно обозначить параметр reload как true.

	reload: false


## Тестирование

	python -m pytest .

# Coming next
Новые источники данных.

Новые модели.

Онлайн-дешборд.