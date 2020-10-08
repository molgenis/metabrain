"""
File:         create_cohort_matrix.py
Created:      2020/10/08
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
import os

# Third party imports.
import pandas as pd

# Local application imports.
from matrix_preparation.src.utilities import prepare_output_dir, check_file_exists, load_dataframe, save_dataframe, construct_dict_from_df


class CreateCohortMatrix:
    def __init__(self, settings, sample_order, force, outdir):
        self.inpath = settings["info_datafile"]
        self.sample_id = settings["sample_id"]
        self.cohort_id = settings["cohort_id"]
        self.sample_order = sample_order
        self.force = force

        # Prepare an output directory.
        self.outdir = os.path.join(outdir, 'create_cohort_matrix')
        prepare_output_dir(self.outdir)
        self.outpath = os.path.join(self.outdir, "cohort_matrix.txt.gz")

        # Declare variables.
        self.sample_info_df = None
        self.cohort_df = None

    def start(self):
        print("Starting creating sample matrix.")
        self.print_arguments()
        # Check if output file exist.
        if check_file_exists(self.outpath) and not self.force:
            print("Skipping step, loading result.")
            self.cohort_df = load_dataframe(inpath=self.outpath,
                                            header=None,
                                            index_col=None)
        else:
            # Load the sample info.
            self.sample_info_df = load_dataframe(inpath=self.outpath,
                                                 header=None,
                                                 index_col=None,
                                                 low_memory=False)

            # Construct sample-cohort dict.
            sample_cohort_dict = construct_dict_from_df(self.sample_info_df,
                                                        self.sample_id,
                                                        self.cohort_id)

            # Load each GTE file.
            self.cohort_df = self.create_cohort_df(self.sample_order,
                                                   sample_cohort_dict)
            self.save()

    @staticmethod
    def create_cohort_df(sample_order, sample_cohort_dict):
        cohort_df = pd.DataFrame(0,
                                 index=sample_cohort_dict.values(),
                                 columns=sample_order)

        for sample in sample_order:
            cohort_df.loc[sample_cohort_dict[sample], sample] = 1

        # Validate.
        if not cohort_df.sum(axis=1).all():
            print("\tSome samples do not have a cohort.")
            exit()

        return cohort_df

    def save(self):
        save_dataframe(df=self.cohort_df, outpath=self.outpath,
                       index=True, header=True)

    def clear_variables(self):
        self.inpath = None
        self.sample_dict = None
        self.sample_order = None
        self.force = None

    def get_outpath(self):
        return self.outpath

    def get_sample_info_df(self):
        return self.sample_info_df

    def get_cohort_df(self):
        return self.cohort_df

    def print_arguments(self):
        print("Arguments:")
        print("  > Input file: {}".format(self.inpath))
        print("  > Sample ID: {}".format(self.sample_id))
        print("  > Cohort ID: {}".format(self.cohort_id))
        print("  > Output path: {}".format(self.outpath))
        print("  > Force: {}".format(self.force))
        print("")
