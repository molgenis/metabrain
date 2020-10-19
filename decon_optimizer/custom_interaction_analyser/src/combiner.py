"""
File:         combiner.py
Created:      2020/10/15
Last Changed: 2020/10/16
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
from __future__ import print_function
from pathlib import Path
from bisect import bisect_left
from itertools import groupby, count
import random
import pickle
import glob
import time
import os

# Third party imports.
import numpy as np
import pandas as pd
from scipy import stats

# Local application imports.
from local_settings import LocalSettings
from utilities import save_dataframe


class Combine:
    def __init__(self, name, settings_file, alpha):
        self.alpha = alpha

        # Define the current directory.
        current_dir = str(Path(__file__).parent.parent)

        # Load the LocalSettings singelton class.
        settings = LocalSettings(current_dir, settings_file)

        # Prepare an output directory.
        self.outdir = os.path.join(current_dir, name)

        # Get the needed settings.
        self.cov_outdir = settings.get_setting("covariates_folder")
        self.tech_cov_outdir = settings.get_setting("technical_covariates_folder")
        self.pvalues_filename = settings.get_setting("real_pvalues_pickle_filename")
        self.snp_coef_filename = settings.get_setting("snp_coef_pickle_filename")
        self.snp_std_err_filename = settings.get_setting("snp_std_err_pickle_filename")
        self.snp_tvalue_filename = settings.get_setting("snp_tvalue_pickle_filename")
        self.inter_coef_filename = settings.get_setting("inter_coef_pickle_filename")
        self.inter_std_err_filename = settings.get_setting("inter_std_err_pickle_filename")
        self.inter_tvalue_filename = settings.get_setting("inter_tvalue_pickle_filename")
        self.perm_pvalues_filename = settings.get_setting("permuted_pvalues_pickle_filename")
        self.n_perm = settings.get_setting("n_permutations")

    def start(self):
        print("Starting interaction analyser - combine and plot.")
        self.print_arguments()

        # Start the timer.
        start_time = time.time()

        for outdir in [self.cov_outdir, self.tech_cov_outdir]:
            full_outdir = os.path.join(self.outdir, outdir)
            print("Working on {}.".format(full_outdir))

            if not os.path.exists(full_outdir):
                print("Error, {} does not exist.".format(os.path.basename(full_outdir)))
                continue

            self.work(full_outdir)

        # Print the time.
        run_time_min, run_time_sec = divmod(time.time() - start_time, 60)
        run_time_hour, run_time_min = divmod(run_time_min, 60)
        print("finished in  {} hour(s), {} minute(s) and "
              "{} second(s).".format(int(run_time_hour),
                                     int(run_time_min),
                                     int(run_time_sec)), flush=True)

    def work(self, workdir):
        dataframes = {}

        print("")
        print("### Step 1 ###")
        print("Combine pickle files into dataframe.", flush=True)
        for filename in [self.pvalues_filename,
                         self.snp_coef_filename,
                         self.snp_std_err_filename,
                         self.inter_coef_filename,
                         self.inter_std_err_filename]:

            print("\tLoading {} data.".format(filename), flush=True)
            columns, data = self.combine_pickles(workdir,
                                                 filename,
                                                 columns=True)

            if len(data) == 0:
                print("\t\tNo {} data found.".format(filename))
                continue

            print("Creating {} dataframe.".format(filename), flush=True)
            df = self.create_df(data, columns)

            print("Saving {} dataframe.".format(filename), flush=True)
            save_dataframe(df=df,
                           outpath=os.path.join(workdir,
                                                "{}_table.txt.gz".format(filename)),
                           header=True, index=True)

            dataframes[filename] = df.copy()

            del columns, data, df

        print("")
        print("### Step 2 ###")
        print("Calculate t-values", flush=True)
        for type, coef_file, std_err_file, tvalue_file in [["SNP", self.snp_coef_filename, self.snp_std_err_filename, self.snp_tvalue_filename],
                                                           ["inter", self.inter_coef_filename, self.inter_std_err_filename, self.inter_tvalue_filename]]:
            if coef_file not in dataframes or std_err_file not in dataframes:
                print("\tNo {} data found.".format(type))
                continue

            coef_df = dataframes[coef_file]
            std_err_df = dataframes[std_err_file]
            tvalue_df = coef_df / std_err_df

            print("Saving {} dataframe.".format(tvalue_file), flush=True)
            save_dataframe(df=tvalue_df,
                           outpath=os.path.join(workdir,
                                                "{}_table.txt.gz".format(tvalue_file)),
                           header=True, index=True)

        print("")
        print("### Step 3 ###")
        print("Starting other calculations", flush=True)

        if self.pvalues_filename not in dataframes:
            print("\tNo pvalues data found.")
            return

        pvalue_df = dataframes[self.pvalues_filename]
        pvalue_df_columns = ["{}_{}".format(x, i) for i, x in enumerate(pvalue_df.columns)]
        pvalue_df.columns = pvalue_df_columns
        pvalue_df_indices = ["{}_{}".format(x, i) for i, x in enumerate(pvalue_df.index)]
        pvalue_df.index = pvalue_df_indices
        pvalue_df.reset_index(drop=False, inplace=True)

        print("Melting dataframe.", flush=True)
        dfm = pvalue_df.melt(id_vars=["index"])
        dfm.columns = ["covariate", "SNP", "pvalue"]
        dfm = dfm.sort_values(by="pvalue", ascending=True)
        dfm.reset_index(drop=True, inplace=True)
        n_signif = dfm[dfm["pvalue"] < self.alpha].shape[0]
        n_total = dfm.shape[0]
        print("\t{}/{} [{:.2f}%] of pvalues < {}".format(n_signif, n_total, (100/n_total)*n_signif, self.alpha), flush=True)

        print("Adding z-scores.", flush=True)
        dfm["zscore"] = stats.norm.isf(dfm["pvalue"])
        dfm.loc[dfm["pvalue"] > (1.0 - 1e-16), "zscore"] = -8.209536151601387
        dfm.loc[dfm["pvalue"] < 1e-323, "zscore"] = 38.44939448087599

        print("Adding BH-FDR.", flush=True)
        dfm["BH-FDR"] = dfm["pvalue"] * (n_total / (dfm.index + 1))
        dfm.loc[dfm["BH-FDR"] > 1, "BH-FDR"] = 1
        prev_bh_fdr = -np.Inf
        for i in range(n_total):
            bh_fdr = dfm.loc[i, "BH-FDR"]
            if bh_fdr > prev_bh_fdr:
                prev_bh_fdr = bh_fdr
            else:
                dfm.loc[i, "BH-FDR"] = prev_bh_fdr
        n_signif = dfm[dfm["BH-FDR"] < self.alpha].shape[0]
        print("\t{}/{} [{:.2f}%] of BH-FDR values < {}".format(n_signif, n_total, (100/n_total)*n_signif, self.alpha), flush=True)

        print("Adding permutation FDR.", flush=True)
        print("\tLoading permutation pvalue data.", flush=True)
        _, perm_pvalues = self.combine_pickles(workdir,
                                               self.perm_pvalues_filename)
        # perm_pvalues = [random.random() for _ in range(n_total * 10)]
        print("Sorting p-values.", flush=True)
        perm_pvalues = sorted(perm_pvalues)

        if len(perm_pvalues) > 0:
            n_perm = len(perm_pvalues) / n_total
            if n_perm != self.n_perm:
                print("\tWARNING: not all permutation pvalus are present")
            perm_ranks = []
            for pvalue in dfm["pvalue"]:
                perm_ranks.append(bisect_left(perm_pvalues, pvalue))
            dfm["perm-rank"] = perm_ranks
            dfm["perm-FDR"] = (dfm["perm-rank"] / n_perm) / dfm.index
            dfm.loc[(dfm.index == 0) | (dfm["perm-rank"] == 0), "perm-FDR"] = 0
            dfm.loc[dfm["perm-FDR"] > 1, "perm-FDR"] = 1

        print("Saving full dataframe.", flush=True)
        save_dataframe(df=dfm,
                       outpath=os.path.join(workdir,
                                            "molten_table.txt.gz"),
                       header=True, index=True)

        print("")
        print("### Step 4 ###")
        print("Saving seperate dataframes.", flush=True)

        for col in ["zscore", "BH-FDR", "perm-FDR"]:
            if col in dfm.columns:
                print("Pivoting table.", flush=True)
                pivot_df = dfm.pivot(index='covariate', columns='SNP', values=col)

                print("Reorder dataframe.")
                pivot_df = pivot_df.loc[pvalue_df_indices, pvalue_df_columns]
                pivot_df.index = ["_".join(x.split("_")[:-1]) for x in pivot_df.index]
                pivot_df.index.name = "-"
                pivot_df.columns = ["_".join(x.split("_")[:-1]) for x in pivot_df.columns]
                pivot_df.columns.name = None

                print("Saving {} dataframe.".format(col), flush=True)
                save_dataframe(df=pivot_df,
                               outpath=os.path.join(workdir,
                                                    "{}_table.txt.gz".format(col)),
                               header=True, index=True)

        print("")

    @staticmethod
    def combine_pickles(indir, filename, columns=False):
        # Declare variables.
        col_list = None
        data = []

        # Combine the found files.
        for i, fpath in enumerate(glob.glob(os.path.join(indir, filename,
                                                         filename + "*.pkl"))):
            with open(fpath, "rb") as f:
                try:
                    content = pickle.load(f)
                    if columns and i == 0:
                        col_list = content[0]
                    data.extend(content[1:])
                except EOFError:
                    print("\tEOFError in: {} ".format(os.path.basename(fpath)))
            f.close()

        return col_list, data

    def create_df(self, data, columns):
        # Crate the data frame.
        df = pd.DataFrame(data, columns=columns)
        order_col = df.columns[0]
        df.sort_values(by=order_col, inplace=True)
        print("\tInput shape: {}".format(df.shape))

        # Check what eQTLs are present, missing, duplicated.
        reference = set(np.arange(df[order_col].min(), df[order_col].max() + 1))
        present = set(df[order_col])
        print("\tPresent indices: {}".format(self.group_consecutive_numbers(present)))
        missing = list(set(df[order_col]).symmetric_difference(reference))
        print("\tMissing indices: {}".format(self.group_consecutive_numbers(missing)))
        duplicated = list(df.loc[df.duplicated([order_col]), order_col].values)
        print("\tDuplicate indices: {}".format(self.group_consecutive_numbers(duplicated)))

        # Remove duplicate eQTLs.
        df.drop_duplicates(subset=order_col, keep="first", inplace=True)

        # Insert missing eQTLs.
        if len(missing) > 0:
            print("\tInserting missing indices")
            missing_df = pd.Series(missing).to_frame()
            missing_df.columns = [order_col]
            df = pd.concat([df, missing_df], axis=0).reset_index(drop=True)
            df.sort_values(by=order_col, inplace=True)

        # Remove the eQTL order column and set the SNPName as index.
        df.drop([order_col], axis=1, inplace=True)
        df.set_index("-", inplace=True)
        df = df.T
        print("\tOutput shape: {}".format(df.shape))

        return df

    @staticmethod
    def group_consecutive_numbers(numbers):
        groups = groupby(numbers, key=lambda item, c=count(): item - next(c))
        tmp = [list(g) for k, g in groups]
        return [str(x[0]) if len(x) == 1 else "{}-{}".format(x[0], x[-1]) for x in tmp]

    def print_arguments(self):
        print("Arguments:")
        print("  > Alpha: {}".format(self.alpha))
        print("  > Output directory: {}".format(self.outdir))
        print("")