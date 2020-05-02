import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def plot_errors(scores, summary, source_id=None, graph_type="map", geodata=None, height=450):
    region_errors = scores.reset_index().groupby(["region_code", "geoname_code"]).sum()
    if source_id is None:
        region_errors = region_errors.sum(1)
    else:
        region_errors = region_errors[source_id]
    region_errors = region_errors.reset_index()
    region_errors.columns = list(region_errors.columns[:-1]) + ["error"]
    title = f'Cumulative region error {"for " + source_id if source_id else "combined"}'

    if graph_type == "map":
        fig = px.choropleth_mapbox(
            region_errors,
            geojson=geodata,
            locations="geoname_code",
            featureidkey="properties.HASC_1",
            color="error",
            range_color=[0, region_errors.mean()["error"] * 2],
        )
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=0.8,
            mapbox_center={"lat": 61.5, "lon": 105},
            height=height,
            margin={"r":0,"t":0,"l":0,"b":2}
        )
        return fig
    elif graph_type == "pie":
        err = region_errors.sort_values(by="error", ascending=False).copy()
        err = err[:15].append(
            pd.DataFrame([["OTHER", "", err[15:]["error"].sum()]], columns=err.columns)
        )
        err["region"] = err["region_code"].apply(
            lambda x: summary.loc[x, "name_with_type"] if x in summary.index else x
        )
        fig = px.pie(err, values="error", names="region", title=title)
        return fig
    else:
        raise ValueError(f"Wrong {graph_type} type")


def plot_predictions(
    predictions, names, data_source, group="region", value="RU-MOW", key="confirmed", height=None
):
    local_data = data_source.reset_index()
    local_data = local_data.query(f'date > "{local_data["date"].values[-12]}"')
    local_data = local_data.set_index(group).loc[value]
    dates = local_data["date"]
    title = f"Predictions for {group} {value} ({key})"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=local_data[key],
            mode="lines+markers",
            name="Source data",
            marker=dict(size=10,),
        )
    )
    for pred_idx, preds in enumerate(predictions):
        local_pred = preds.reset_index().set_index(group).loc[value]
        local_pred = local_pred.query(
            f'date >= "{min(dates)}" & date <= "{max(dates)}"'
        )
        fig.add_trace(
            go.Scatter(
                x=local_pred["date"],
                y=local_pred["prediction_" + key],
                mode="lines+markers",
                name=names[pred_idx],
            )
        )
    fig.update_layout(title=title)
    if height is not None:
        fig.update_layout(height=height)
    return fig
