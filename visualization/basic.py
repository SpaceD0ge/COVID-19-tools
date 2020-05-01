import plotly.express as px
import plotly.graph_objects as go
import numpy as np


def plot_map(
    data, title, color_key,
    color_scale,
    geodata=None,
    hover_name=None,
    animation_frame=None,
    center={"lat": 61.5, "lon": 105},
    map_style="carto-positron",
    map_class="choropleth",
):
    if map_class == "choropleth":
        map_figure = px.choropleth
    elif map_class == "choropleth_mapbox" or map_class == "mapbox":
        map_figure = px.choropleth_mapbox
    else:
        raise ValueError(f"Wrong map type {map_class}")
    fig = map_figure(
        data,
        geojson=geodata,
        locations="geoname_code",
        featureidkey="properties.HASC_1",
        color=color_key,
        animation_frame=animation_frame,
        range_color=[data[color_key].min(), data[color_key].max() * 1.3],
        hover_name=hover_name,
        hover_data=[color_key],
        center=center,
        color_continuous_scale=color_scale,
    )

    fig.update_layout(
        mapbox_style=map_style, mapbox_zoom=1, mapbox_center=center,
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    fig.update_layout(
        annotations=[
            dict(text=title, showarrow=False, xref="paper", yref="paper", x=0, y=1.00)
        ]
    )
    return fig


def plot_country_dynamic(
    data, start="2020-03-06", key="confirmed", group="region_name", clip=None
):
    if start:
        data = data.query(f'date > "{start}"')
    if clip:
        date = data["date"].max()
        selected = data[data["date"] == date].sort_values(by="cases")[-clip:][group]
        data = data.set_index(group).loc[selected].reset_index()
    fig = px.line(data, x="date", y=key, color=group)
    fig.update_layout(yaxis_type="log")
    fig.update_layout(dict(title="Country dynamics for confirmed cases"))
    return fig


def plot_cases_map(
    data,
    geojson=None,
    key="confirmed",
    group="geoname_code",
    log_scale=False,
    mtype="choropleth",
    center=None,
    date=None,
):
    data["geoname_code"] = data[group]
    if date is None:
        date = data["date"].max()
    local_data = data.query(f'date == "{date}"').copy()
    if log_scale:
        local_data["log_values"] = np.log10(local_data[key])
        key = "log_values"

    postfix = "Log scale" if log_scale else ""
    title = f"Confirmed cases by region by {date}. {postfix}"

    return plot_map(
        local_data, title, key,
        px.colors.sequential.tempo,
        geodata=geojson,
        map_class=mtype,
        center=center,
    )


def plot_region_dynamic(data, region_code, key="confirmed", group="region_name"):
    bar_data = data.reset_index().set_index(group).loc[region_code].query(f"{key} > 5")
    fig = go.Figure(
        [
            go.Bar(x=bar_data["date"], y=bar_data[key], name="cumulative"),
            go.Scatter(x=bar_data["date"], y=bar_data[key].diff(), name="by day"),
        ]
    )
    title = f"Confirmed cases dynamic for {region_code}"
    fig.update_layout(title=title)
    return fig


def plot_simple_difference(
    scores, group="date", graph_type="scatter", cumulative=False
):
    aggregate = scores.reset_index().groupby(group).mean()
    if cumulative:
        aggregate = aggregate.rolling(min_periods=1, window=120).sum()

    aggregate = aggregate.reset_index().melt(
        id_vars=[group], var_name="source_id", value_name="log_error"
    )
    title = "Comparing different predictions"
    if graph_type == "scatter":
        return px.line(
            aggregate, x=group, y="log_error", color="source_id", title=title
        )
    elif graph_type == "bar":
        return px.bar(
            aggregate,
            x=group,
            y="log_error",
            color="source_id",
            barmode="group",
            title=title,
        )
    else:
        raise ValueError(f"Wrong graph type {graph_type}")


def plot_map_difference(
    scores,
    geojson,
    group="geoname_code",
    by_source=False,
    mtype="choropleth",
    center=None,
):
    agg = scores.reset_index().groupby(group).mean()
    if by_source:
        agg["best"] = agg.apply(lambda x: np.argmin(x), 1)
        agg.reset_index(inplace=True)
        key = "best"
        animation = None
        title = "Comparing different predictions by best index"
        scale = color_continuous_scale = px.colors.sequential.Rainbow
    else:
        agg = agg.reset_index().melt(
            id_vars=["geoname_code"], var_name="source", value_name="error"
        )
        key = "error"
        animation = "source"
        title = "Comparing different predictions by region error values"
        scale = px.colors.sequential.Reds
    fig = plot_map(
        agg, title, key,
        scale,
        animation_frame=animation,
        geodata=geojson,
        map_class=mtype,
        center=center,
    )

    if not by_source:
        fig.update_layout(coloraxis={"cmax": agg.error.max(), "cmin": agg.error.min()})

    return fig


__all__ = [
    "plot_region_dynamic",
    "plot_country_dynamic",
    "plot_simple_difference",
    "plot_map_difference",
    "plot_cases_map",
]
