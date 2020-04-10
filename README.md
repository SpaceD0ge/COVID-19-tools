# Tools for the COVID-19 information processing.
Prediction models for the current Sberbank competition.

[![CodeFactor](https://www.codefactor.io/repository/github/spaced0ge/covid-19-tools/badge)](https://www.codefactor.io/repository/github/spaced0ge/covid-19-tools)
[![Build Status](https://travis-ci.com/SpaceD0ge/competition.svg?branch=master)](https://travis-ci.com/SpaceD0ge/competition)

## Data sources

[Oxford COVID-19 Government Response Tracker](https://www.bsg.ox.ac.uk/research/research-projects/oxford-covid-19-government-response-tracker)

Stringency ratings for different government responses.

[Google COVID-19 Community Mobility Reports](https://www.google.com/covid19/mobility/)

Mobility trends for different areas and types of places.

[2019-nCoV Data Repository by Johns Hopkins CSSE](https://github.com/CSSEGISandData/COVID-19/)

Tracking cases by country.

## Requirements

python 3.5+
internet access

## Configuration format

The main file configuration parameters can be found in the file_cfg.yml.
Each of the main data parsers should have a root folder. Set to "./report_files" by default.
 
	root: ./report_files

This competition follows the "iso_alpha3" naming convention. The "countries.csv" file holds some additional information.

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
