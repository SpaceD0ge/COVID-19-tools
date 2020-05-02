import numpy as np
import pandas as pd


def ale(true, predicted):
    """
    Absolute Log Error
    """
    return np.abs(np.log10((predicted + 1) / (true + 1)))


def collect_scores(true_values, pred_df):
    """
    Collects log error scores between predicted and original dataframes.
    """
    csv_data = []
    for index in true_values.index.unique():
        if index not in pred_df.index:
            continue
        true_confirmed = true_values.loc[index]["confirmed"]
        pred_confirmed = pred_df.loc[index]["prediction_confirmed"]

        csv_data.append(
            [
                index[0],
                index[1],
                true_values.loc[index]["geoname_code"],
                ale(true_confirmed, pred_confirmed),
            ]
        )

    csv_data = pd.DataFrame(csv_data)
    csv_data.columns = ["region_code", "date", "geoname_code", "cases_male"]
    return csv_data.set_index(["region_code", "geoname_code", "date"])


def get_validation_results(
    predictions,
    test_source,
    start,
    end,
    summary_df,
    key="region",
    name_col="csse_province_state",
    custom_ids=None,
):
    """
    Validates multiple predictions at a time for a specified date range.
        predictions = list of dataframes with predictions (submissions)
        test_source = original data to compare with
        start = starting date in format "%Y-%m-%d"
        end = ending date in format "%Y-%m-%d"
        summary_df = regions summary information dataframe
        key = column with region/country codes
        name_col = column with region/country names
        custom_ids = None or list of strings with distinct team ids
    """
    fixed_predictions = []
    for prediction_df in predictions:
        preds = prediction_df.copy()
        preds["geoname_code"] = preds[key].apply(
            lambda x: summary_df.loc[x, "geoname_code"]
        )
        preds["region_name"] = preds[key].apply(lambda x: summary_df.loc[x, name_col])
        preds = preds.query(f'date >= "{start}" & date <= "{end}"').set_index(
            ["region", "date"]
        )
        fixed_predictions.append(preds)

    test_source["date"] = pd.to_datetime(test_source.date).dt.strftime("%Y-%m-%d")
    true_values = (
        test_source.query(f'date >= "{start}" & date <= "{end}"')
        .reset_index()
        .set_index(["region", "date"])
    )

    scores = pd.concat(
        [collect_scores(true_values, preds) for preds in fixed_predictions], 1
    )
    if custom_ids is None:
        scores.columns = [f"source_{x}" for x in range(len(scores.columns))]
    else:
        scores.columns = custom_ids
    return scores
