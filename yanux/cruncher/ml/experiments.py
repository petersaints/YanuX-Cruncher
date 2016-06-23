import collections
import random

import numpy as np
import pandas as pd
import sklearn.metrics
from sklearn.neighbors import KNeighborsRegressor


def experiment_metrics(result):
    base_error = pd.DataFrame(0, index=np.arange(len(result)), columns=["error"])
    metrics = collections.OrderedDict([("mean_absolute_error", result["error"].mean()),
                                       ("std_dev_distance_error", result["error"].std()),
                                       ("mean_squared_error", sklearn.metrics.mean_squared_error(base_error,
                                                                                                 result["error"])),
                                       ("percentile_25", result["error"].quantile(q=0.25)),
                                       ("percentile_50", result["error"].quantile(q=0.50)),
                                       ("percentile_75", result["error"].quantile(q=0.75)),
                                       ("percentile_90", result["error"].quantile(q=0.90)),
                                       ("percentile_95", result["error"].quantile(q=0.95)),
                                       ("min", result["error"].min()),
                                       ("max", result["error"].max())])
    return metrics


def knn_experiment(data, train_cols, coord_cols,
                   n_neighbors=5, weights='uniform', algorithm='auto',
                   leaf_size=30, p=2, metric='minkowski',
                   metric_params=None, n_jobs=1,
                   test_data=None):
    result = None
    knn = KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights, algorithm=algorithm,
                              leaf_size=leaf_size, p=p, metric=metric,
                              metric_params=metric_params, n_jobs=n_jobs)
    locations = data.groupby(coord_cols).indices.keys()
    for coords in locations:
        train_data = data[(data[coord_cols[0]] != coords[0]) |
                          (data[coord_cols[1]] != coords[1])].reset_index(drop=True)
        if test_data is not None:
            target_values = test_data[(test_data[coord_cols[0]] == coords[0]) &
                                      (test_data[coord_cols[1]] == coords[1])].reset_index(drop=True)
        else:
            target_values = data[(data[coord_cols[0]] == coords[0]) &
                                 (data[coord_cols[1]] == coords[1])].reset_index(drop=True)
        knn.fit(train_data[train_cols], train_data[coord_cols])
        predictions = pd.DataFrame(knn.predict(target_values[train_cols]), columns=coord_cols)
        curr_result = target_values[coord_cols].join(predictions, rsuffix="_predicted")
        error = pd.DataFrame((predictions[["x", "y"]] - curr_result[["x", "y"]]).apply(np.linalg.norm, axis=1),
                             columns=["error"])
        curr_result = pd.concat([curr_result, error], axis=1)
        result = pd.concat([result, curr_result])

    return result


def convert_to_units(data, from_units="dBm", to_units="dBm"):
    if from_units == "dBm" and to_units == "dBm":
        return data
    elif from_units == "dBm" and to_units == "mW":
        return 10 ** (data / 10)
    elif from_units == "mW" and to_units == "dBm":
        return 10 * np.log10(data)
    else:
        raise ValueError("Unsupported units")


def subset_wifi_samples_locations(wifi_samples, kept_locations_ratio=1.0, aggregation_coords=["x", "y", "floor"], ):
    locations_coords = wifi_samples.groupby(aggregation_coords).indices
    sampled_locations_coords_keys = random.sample(list(locations_coords),
                                                  int(len(locations_coords) * kept_locations_ratio))
    ids = []
    for key in sampled_locations_coords_keys:
        ids.extend(locations_coords[key])
    return wifi_samples.ix[ids].reset_index(drop=True)


def prepare_full_data_scenarios(wifi_samples, data_scenarios, aggregation_coords=["x", "y", "floor"],
                                raw=True, groupby_mean=False, groupby_min=False, groupby_max=False,
                                scenarios_suffix=None):
    if raw or groupby_mean or groupby_max or groupby_min:
        if scenarios_suffix:
            scenario_parameters = "_" + scenarios_suffix
        else:
            scenario_parameters = ""
        full_data = wifi_samples.copy()
        if raw:
            data_scenarios["full_data" + scenario_parameters] = full_data
        if groupby_mean or groupby_max or groupby_min:
            full_groupby_data = wifi_samples.groupby(aggregation_coords, as_index=False)
            if groupby_mean:
                data_scenarios["full_groupby_mean_data" + scenario_parameters] = full_groupby_data.mean()
            if groupby_max:
                data_scenarios["full_groupby_max_data" + scenario_parameters] = full_groupby_data.max()
            if groupby_min:
                data_scenarios["full_groupby_min_data" + scenario_parameters] = full_groupby_data.min()
    return data_scenarios


def prepare_partial_data_scenarios(wifi_samples, data_scenarios, aggregation_coords=["x", "y", "floor"],
                                   slice_at_the_end=False, partials=[0.5],
                                   raw=True, groupby_mean=False, groupby_min=False, groupby_max=False,
                                   scenarios_suffix=""):
    if raw or groupby_mean or groupby_max or groupby_min:
        if scenarios_suffix:
            scenarios_suffix = "_" + scenarios_suffix
        else:
            scenarios_suffix = ""
        locations_coords = wifi_samples.groupby(aggregation_coords).indices.items()
        for frac in partials:
            scenario_parameters = "_fraction=" + str(frac) + scenarios_suffix
            ids = []
            for key, indices in locations_coords:
                if not slice_at_the_end:
                    slice_index = int(len(indices) * frac)
                    ids.extend(indices[:slice_index])
                else:
                    slice_index = int(len(indices) * (1.0 - frac))
                    ids.extend(indices[slice_index:])
                partial_data = wifi_samples.ix[ids].reset_index(drop=True)
                if raw:
                    data_scenarios["partial_data" + scenario_parameters] = partial_data
                if groupby_mean or groupby_max or groupby_min:
                    partial_groupby_data = partial_data.groupby(aggregation_coords, as_index=False)
                    if groupby_mean:
                        partial_groupby_mean_data = partial_groupby_data.mean()
                        data_scenarios["partial_groupby_mean_data" + scenario_parameters] = partial_groupby_mean_data
                    if groupby_max:
                        partial_groupby_max_data = partial_groupby_data.max()
                        data_scenarios["partial_groupby_max_data" + scenario_parameters] = partial_groupby_max_data
                    if groupby_min:
                        partial_groupby_min_data = partial_groupby_data.min()
                        data_scenarios["partial_groupby_min_data" + scenario_parameters] = partial_groupby_min_data
    return data_scenarios


def prepare_filename_startswith_data_scenarios(wifi_samples, data_scenarios,
                                               filename_startswith="", aggregation_coords=["x", "y", "floor"],
                                               raw=True, groupby_mean=False, groupby_min=False, groupby_max=False,
                                               scenarios_suffix=""):
    if raw or groupby_mean or groupby_mean or groupby_max or groupby_min:
        if scenarios_suffix:
            scenarios_suffix = "_" + scenarios_suffix
        else:
            scenarios_suffix = ""
        scenario_parameters = "_" + filename_startswith + scenarios_suffix
        filename_startswith_data = wifi_samples[
            wifi_samples["filename"].str.startswith(filename_startswith)].reset_index(drop=True)
        if raw:
            data_scenarios["filename_startswith_data" + scenario_parameters] = filename_startswith_data
        if groupby_mean or groupby_max or groupby_min:
            filename_startswith_groupby_data = filename_startswith_data.groupby(aggregation_coords, as_index=False)
            if groupby_mean:
                filename_startswith_groupby_mean_data = filename_startswith_groupby_data.mean()
                data_scenarios[
                    "filename_startswith_groupby_mean_data" + scenario_parameters] = filename_startswith_groupby_mean_data
            if groupby_max:
                filename_startswith_groupby_max_data = filename_startswith_groupby_data.max()
                data_scenarios[
                    "filename_startswith_groupby_max_data" + scenario_parameters] = filename_startswith_groupby_max_data
            if groupby_min:
                filename_startswith_groupby_min_data = filename_startswith_groupby_data.min()
                data_scenarios[
                    "filename_startswith_groupby_min_data" + scenario_parameters] = filename_startswith_groupby_min_data
    return data_scenarios


def path_direction_aggregated_data_scenarios(wifi_samples, data_scenarios, aggregation_coords=["x", "y", "floor"],
                                             groupby_mean=False, groupby_max=True, groupby_min=False,
                                             scenarios_suffix=""):
    if groupby_mean or groupby_max or groupby_min:
        path_direction_aggregated_data = wifi_samples.groupby(["x", "y", "floor", "filename" + scenarios_suffix],
                                                              as_index=False).mean()
        if groupby_mean:
            path_direction_aggregated_mean_data = path_direction_aggregated_data.groupby(aggregation_coords,
                                                                                         as_index=False).mean()
            data_scenarios[
                "path_direction_aggregated_mean_data" + scenarios_suffix] = path_direction_aggregated_mean_data
        if groupby_max:
            path_direction_aggregated_max_data = path_direction_aggregated_data.groupby(aggregation_coords,
                                                                                        as_index=False).max()
            data_scenarios["path_direction_aggregated_max_data" + scenarios_suffix] = path_direction_aggregated_max_data
        if groupby_min:
            path_direction_aggregated_min_data = path_direction_aggregated_data.groupby(aggregation_coords,
                                                                                        as_index=False).min()
            data_scenarios["path_direction_aggregated_min_data" + scenarios_suffix] = path_direction_aggregated_min_data
    return data_scenarios


def save_scenarios(data_scenarios, output_directory="out", prefix=""):
    for data_scenario_name, data_scenario in data_scenarios.items():
        data_scenario["scenario_name"] = prefix + data_scenario_name
        data_scenario.to_csv(output_directory + "/" + prefix + data_scenario_name + ".csv")

# TODO: Remove if I end up never using it again!
# def _prepare_shuffled_partial_data_scenarios_aux(wifi_samples, shuffled_indices, data_scenarios, aggregation_coords,
#                                                  run, slice_at_the_end, partials,
#                                                  raw, groupby_mean, groupby_max, groupby_min, scenarios_suffix):
#     if raw or groupby_mean or groupby_max or groupby_min:
#         if scenarios_suffix:
#             scenarios_suffix = "_" + scenarios_suffix
#         else:
#             scenarios_suffix = ""
#         for frac in partials:
#             scenario_parameters = "_fraction=" + str(frac) + ",_run=" + str(run) + scenarios_suffix
#             data_ids = []
#             for key, indices in shuffled_indices.items():
#                 data_slice_index = int(len(shuffled_indices) * frac)
#                 if slice_at_the_end is not True:
#                     data_ids.extend(indices[:data_slice_index])
#                 else:
#                     data_ids.extend(indices[data_slice_index:])
#             partial_data = wifi_samples.ix[data_ids].reset_index(drop=True)
#             if raw:
#                 data_scenarios["shuffled_partial_data" + scenario_parameters] = partial_data
#             if groupby_mean or groupby_max or groupby_min:
#                 partial_groupby_data = partial_data.groupby(aggregation_coords, as_index=False)
#                 if groupby_mean:
#                     partial_groupby_mean_data = partial_groupby_data.mean()
#                     data_scenarios[
#                         "shuffled_partial_groupby_mean_data" + scenario_parameters] = partial_groupby_mean_data
#                 if groupby_max:
#                     partial_groupby_max_data = partial_groupby_data.max()
#                     data_scenarios["shuffled_partial_groupby_max_data" + scenario_parameters] = partial_groupby_max_data
#                 if groupby_min:
#                     partial_groupby_min_data = partial_groupby_data.min()
#                     data_scenarios["shuffled_partial_groupby_min_data" + scenario_parameters] = partial_groupby_min_data
#     return data_scenarios
#
#
# def prepare_shuffled_partial_data_scenarios(wifi_samples, data_scenarios, test_data_scenarios,
#                                             aggregation_coords=["x", "y", "floor"],
#                                             shuffled_runs=3, partials=[0.5], test_partials=[0.5],
#                                             raw=True, groupby_mean=False, groupby_max=False, groupby_min=False,
#                                             scenarios_suffix=""):
#     if raw or groupby_mean or groupby_max or groupby_min:
#         locations_coords = wifi_samples.groupby(aggregation_coords).indices.items()
#         for run in range(0, shuffled_runs):
#             shuffled_indices = {}
#             for key, indices in locations_coords:
#                 shuffled_indices[key] = indices.copy()
#                 random.shuffle(shuffled_indices[key])
#             _prepare_shuffled_partial_data_scenarios_aux(wifi_samples, shuffled_indices, data_scenarios,
#                                                          aggregation_coords,
#                                                          run, False, partials,
#                                                          raw, groupby_mean, groupby_max, groupby_min,
#                                                          scenarios_suffix)
#             _prepare_shuffled_partial_data_scenarios_aux(wifi_samples, shuffled_indices, test_data_scenarios,
#                                                          aggregation_coords,
#                                                          run, True, partials,
#                                                          raw, groupby_mean, groupby_max, groupby_min,
#                                                          scenarios_suffix)
