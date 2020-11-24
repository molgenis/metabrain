"""
File:         cohort_object.py
Created:      2020/11/18
Last Changed:
Author:       M.Vochteloo

Copyright (C) 2020 M.Vochteloo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

A copy of the GNU General Public License can be found in the LICENSE file in the
root directory of this source tree. If not, see <https://www.gnu.org/licenses/>.
"""

# Standard imports.

# Third party imports.
import pandas as pd
from scipy import stats

# Local application imports.


class Cohort:
    def __init__(self, cohort, samples, geno_df, expr_df, cf_df,
                 log):
        self.cohort = cohort
        self.samples = samples
        self.geno_df = geno_df
        self.expr_df = expr_df
        self.cf_df = cf_df
        self.log = log

        # Initialize normalized data frames.
        self.normal_geno_df = None
        self.normal_expr_df = None
        self.normal_cf_df = None

    def contains_sample(self, sample):
        return sample in self.samples

    def get_geno_df(self):
        return self.geno_df

    def get_normal_geno_df(self):
        if self.normal_geno_df is None:
            self.normal_geno_df = self.force_normal(self.geno_df)

        return self.normal_geno_df

    def get_expr_df(self):
        return self.expr_df

    def get_normal_expr_df(self):
        if self.normal_expr_df is None:
            self.normal_expr_df = self.force_normal(self.expr_df)

        return self.normal_expr_df

    def get_cf_df(self):
        return self.cf_df

    def get_normal_cf_df(self):
        if self.normal_cf_df is None:
            self.normal_cf_df = self.force_normal(self.cf_df, value_axis=0)

        return self.normal_cf_df

    def force_normal(self, df, value_axis=1):
        work_df = df.copy()

        if value_axis == 0:
            work_df = work_df.T
        elif value_axis == 1:
            pass
        else:
            self.log.error("Unexpected axis in force normal function.")
            exit()

        data = []
        for index, row in work_df.iterrows():
            data.append(self.force_normal_series(row))

        normal_df = pd.DataFrame(data, index=work_df.index, columns=work_df.columns)

        if value_axis == 0:
            normal_df = normal_df.T

        return normal_df

    @staticmethod
    def force_normal_series(s, as_series=False):
        normal_s = stats.norm.ppf((s.rank(ascending=True) - 0.5) / s.size)
        if as_series:
            return pd.Series(normal_s, index=s.index)
        else:
            return normal_s

    def calculate_new_normalized_cf_s(self, sample, cell_type, new_value):
        tmp_cf_s = self.cf_df.loc[:, cell_type].copy()
        tmp_cf_s.loc[sample] = new_value
        new_cf_s = self.force_normal_series(tmp_cf_s, as_series=True)
        new_cf_s.name = "new"

        original_normal_values = self.normal_cf_df.loc[:, cell_type].copy()
        original_normal_values.name = "original"

        combined_df = original_normal_values.to_frame().merge(new_cf_s, left_index=True, right_index=True)

        return self.cf_df.loc[sample, cell_type], combined_df.loc[combined_df["new"] != combined_df["original"], "new"]

    def print_info(self):
        self.log.info("Cohort: {}".format(self.cohort))
        self.log.info(" > N-samples: {}".format(self.geno_df.shape[1]))
        self.log.info("")