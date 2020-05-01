import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np


class CustomOverviewGraph:
    def __init__(self, df, geodata):
        self.regions_df = df
        self.geodata = geodata

    def get_pop_map(self, data, date="2020-04-20"):
        local_data = data.query(f'date == "{date}"')
        return go.Choroplethmapbox(
            locations=local_data["geoname_code"],
            geojson=self.geodata,
            text=[
                self.regions_df.loc[x, "name_with_type"]
                for x in local_data["region"].values
            ],
            hoverinfo="all",
            featureidkey="properties.HASC_1",
            z=local_data["confirmed_pop"],
            colorscale=px.colors.sequential.tempo,
            coloraxis="coloraxis",
            name="Russian map",
        )

    def get_bar_ratings(self, data, key="prediction_confirmed", date="2020-04-20"):
        bar_data = data.query(f'date == "{date}"').reset_index()
        bar_data = bar_data.sort_values(by=key)[-15:]
        return go.Bar(
            text=[
                self.regions_df.loc[x, "name_with_type"]
                for x in bar_data["region"].values
            ],
            y=bar_data[key].apply(lambda x: np.log10(x)),
            textposition="inside",
            showlegend=False,
            yaxis="y2",
        )

    def get_dynamic(self, data, key="prediction_confirmed"):
        df_diff = data[["date", key]].groupby("date").sum().diff().dropna()
        return go.Bar(x=df_diff.index, y=df_diff[key], showlegend=False)

    def animate(self, fig, data, key, dates):
        frames = [
            go.Frame(
                data=[
                    go.Bar(visible=True),
                    self.get_bar_ratings(data, key, date),
                    self.get_pop_map(data, date),
                ],
                traces=[0, 1, 2],
                name=date,
            )
            for date in dates
        ]

        steps = [
            dict(
                method="animate",
                args=[
                    [date],
                    dict(
                        mode="e",
                        frame=dict(duration=20, redraw=True),
                        transition=dict(duration=0),
                    ),
                ],
                label=date,
            )
            for date in dates
        ]

        sliders = [dict(steps=steps, active=0)]

        fig.frames = frames
        fig.update_layout(sliders=sliders)

    def get_annotations(self):
        return [
            dict(
                text="% населения с подтвержденным заражением для областей России",
                bgcolor="black", bordercolor="black", borderwidth=1,
                showarrow=False,
                xref="paper", yref="paper",
                x=1, y=1,
            ),
            dict(
                text="Заражений по дням",
                showarrow=False,
                textangle=90,
                xref="paper", yref="paper",
                x=0.4, y=1,
            ),
            dict(
                text="Log шкала заражений",
                showarrow=False,
                textangle=90,
                xref="paper", yref="paper",
                x=0.4, y=0.05,
            ),
        ]

    def fix_axis(self, fig):
        fig.update_layout(
            coloraxis={"colorscale": px.colors.sequential.tempo, "cmax": 0.3, "cmin": 0}
        )
        fig.update_layout(yaxis2={"range": (0, 5)})

    def fix_style(self, fig):
        fig.update_layout(
            title="Распространение COVID-19 по России (подтвержденные случаи заражений)",
            template="plotly_dark",
            mapbox_style="carto-darkmatter",
            mapbox_zoom=1.2,
            mapbox_center={"lat": 65.5, "lon": 105},
            margin=dict(r=20, t=50, b=20, l=30),
            annotations=self.get_annotations(),
        )

    def plot(self, data, key, dates):

        fig = make_subplots(
            rows=2,
            cols=2,
            column_widths=[0.4, 0.6],
            row_heights=[0.5, 0.5],
            specs=[
                [{"type": "bar"}, {"type": "choroplethmapbox", "rowspan": 2}],
                [{"type": "bar"}, None],
            ],
        )

        data = data.query('date > "2020-03-20"').reset_index().copy()
        data["pop"] = data["region"].apply(
            lambda x: self.regions_df.loc[x, "population"]
        )
        data["confirmed_pop"] = 100 * data[key] / data["pop"]
        fig.add_trace(self.get_dynamic(data, key), 1, 1)
        fig.add_trace(self.get_bar_ratings(data, key, dates[0]), 2, 1)
        fig.add_trace(self.get_pop_map(data, dates[0]), 1, 2)

        if len(dates) > 0:
            self.animate(fig, data, key, dates)

        self.fix_axis(fig)
        self.fix_style(fig)

        return fig
