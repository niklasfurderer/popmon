import numpy as np
import pandas as pd
from ..base import Module
import fnmatch


class AlertsSummary(Module):
    """The module AlertsSummary combines the alerts-summaries of all individual features

    It combines the alerts-summaries of all individual features into an artificial feature "_AGGREGATE_".
    """
    def __init__(self, read_key, store_key='', features=None, ignore_features=None, combined_variable='_AGGREGATE_'):
        """Initialize an instance of AlertsSummary module.

        :param str read_key: key of input data to read from datastore.
        :param str store_key: key of output data to store in datastore (optional).
        :param str combined_variable: name of artifical variable that combines all alerts. default is '_AGGREGATE_'.
        :param list features: features of data frames to pick up from input data (optional).
        :param list ignore_features: list of features to ignore (optional).
        """
        super().__init__()
        self.read_key = read_key
        self.store_key = store_key
        if not self.store_key:
            self.store_key = self.read_key
        self.features = features or []
        self.ignore_features = ignore_features or []
        self.combined_variable = combined_variable

    def transform(self, datastore):
        # fetch and check input data
        data = self.get_datastore_object(datastore, self.read_key, dtype=dict)

        # determine all possible features, used for the comparison below
        features = self.get_features(data.keys())
        if len(features) == 0:
            return datastore

        self.logger.info(f'Combining alerts into artificial variable \"{self.combined_variable}\"')

        # STEP 1: loop over features where alerts exist
        df_list = []
        for feature in features:
            # basic checks if feature object is filled correctly
            df = (self.get_datastore_object(data, feature, dtype=pd.DataFrame)).copy(deep=False)
            df.columns = [feature + '_' + c for c in df.columns]
            df_list.append(df)

        # the different features could technically have different indices.
        # will only merge alerts if all indices are the same
        if len(df_list) >= 2:
            for df in df_list[1:]:
                if not np.array_equal(df_list[0].index, df.index):
                    self.logger.warning('indices of features are different. no alerts summary generated.')
                    return datastore

        # STEP 2: Concatenate the dataframes, there was one for each original feature.
        tlv = pd.concat(df_list, axis=1)
        dfc = pd.DataFrame(index=tlv.index)

        # worst traffic light
        cols = fnmatch.filter(tlv.columns, '*_worst')
        dfc['worst'] = tlv[cols].values.max(axis=1) if len(cols) else 0
        # colors of traffic lights
        for color in ["green", "yellow", "red"]:
            cols = fnmatch.filter(tlv.columns, '*_n_{}'.format(color))
            dfc['n_{}'.format(color)] = tlv[cols].values.sum(axis=1) if len(cols) else 0

        # store combination of traffic alerts
        data[self.combined_variable] = dfc
        datastore[self.store_key] = data

        return datastore
