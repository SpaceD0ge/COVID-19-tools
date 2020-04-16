def model_per_country_simple_split(data, targets, index=None, sort_by="date"):
    data_copy = data.copy()
    if index is not None:
        data_copy = data_copy.set_index(index)
    data_copy = data_copy.query(f"{targets[0]} > 0").sort_values(sort_by)

    return (
        (code, {target: data_copy.loc[code, target].values for target in targets})
        for code in data.index.unique()
    )
