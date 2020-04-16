import plotly.graph_objects as go
from datetime import datetime, timedelta


def graph_SEIR(code, opt_result, start_date, plot=True):
    fig = go.Figure()
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    graph_dates = [
        start_date + timedelta(days=x)
        for x in range(len(opt_result["predicted_cases"]))
    ]
    graph_dates = [x.strftime("%Y-%m-%d") for x in graph_dates]

    fig.add_trace(
        go.Scatter(
            x=graph_dates,
            y=[int(x) for x in opt_result["predicted_cases"]],
            mode="lines",
            name="Model outputs",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=graph_dates[: len(opt_result["original_cases"])],
            y=opt_result["original_cases"],
            mode="lines+markers",
            name="Official data",
            marker=dict(size=4),
        )
    )

    fig.update_layout(
        title=f"SEIR model outputs for {code}",
        xaxis_title="Date since the first confirmed case",
        yaxis_title="Confirmed cases",
        autosize=False,
        width=600,
        height=350,
        margin=dict(l=50, r=50, b=50, t=50, pad=4),
    )
    if plot:
        fig.show()
    else:
        return fig


def graph_Rt(code, opt_result, start_date, period=60, plot=True):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    graph_dates = [start_date + timedelta(days=x) for x in range(period)]
    graph_dates = [x.strftime("%Y-%m-%d") for x in graph_dates]
    params = opt_result["parameters"]
    k, L = params[-2:]
    R_0 = params[0]

    def time_varying_reproduction(t):
        return R_0 / (1 + (t / L) ** k)

    Rt = [time_varying_reproduction(x) for x in range(period)]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=graph_dates, y=[1 for _ in range(period)], mode="lines", name="R of 1"
        )
    )
    fig.add_trace(go.Scatter(x=graph_dates, y=Rt, mode="lines", name="Model value",))

    fig.update_layout(
        title=f"SEIR model R parameter reproduction for {code}",
        xaxis_title="Date since the first confirmed case",
        yaxis_title="Value",
        autosize=False,
        width=600,
        height=350,
        margin=dict(l=50, r=50, b=50, t=50, pad=4),
    )

    if plot:
        fig.show()
    else:
        return fig
