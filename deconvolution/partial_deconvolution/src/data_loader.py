"""
File:         data_loader.py
Created:      2020/06/29
Last Changed: 2020/06/30
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
import gzip
import json
import os

# Third party imports.
import numpy as np
import pandas as pd

# Local application imports.


class DataLoader:
    def __init__(self, settings):
        self.data_path = settings.get_data_path()
        self.signature_path = settings.get_signature_path()
        self.translate_path = settings.get_translate_path()
        self.sample_path = settings.get_sample_path()
        self.cohort = settings.get_cohort()
        self.ground_truth_path = settings.get_ground_truth_path()

        outdir = settings.get_output_path()
        self.expression_file = os.path.join(outdir, 'expression_{}.txt.gz'.format(self.cohort))
        self.signature_file = os.path.join(outdir, 'signature.txt.gz')
        self.settings_file = os.path.join(outdir, 'settings.json')

        self.expression = None
        self.signature = None
        self.ground_truth = None

    def work(self):
        # Check if the filtered data files exist.
        if (not os.path.exists(self.signature_file) and not os.path.exists(self.expression_file))\
                or not os.path.exists(self.settings_file) or not self.settings_match():
            print("Loading files")
            self.load()
            self.save()
        else:
            print("Loading saved files")
            self.load_saved_files()

        # Check if ground truth file exists and if so, load it.
        if self.ground_truth_path is not None and os.path.exists(self.ground_truth_path):
            self.load_ground_truth()

    def load(self):
        # Load the signature matrix.
        self.signature = self.load_signature(self.signature_path)

        # Load the expression of the signature genes.
        translate_dict = self.load_translate(self.translate_path)
        sample_dict = self.load_samples(self.sample_path,
                                        self.cohort)
        self.expression = self.load_data(self.data_path,
                                         self.signature.index,
                                         translate_dict,
                                         sample_dict)

    @staticmethod
    def load_signature(filepath):
        print("\tLoading signature matrix")
        df = pd.read_csv(filepath, sep="\t", header=0, index_col=0)
        df.columns = [x.split("_")[1] for x in df.columns]
        return df

    @staticmethod
    def load_translate(filepath, key="ArrayAddress", value="Symbol"):
        print("\tLoading translation dict")
        df = pd.read_csv(filepath, sep="\t", header=0)
        return dict(zip(df.loc[:, key], df.loc[:, value]))

    @staticmethod
    def load_samples(filepath, cohort, key="RnaID", value="GenotypeID"):
        print("\tLoading samples dict")
        df = pd.read_csv(filepath, sep="\t")
        if cohort.lower() != 'All':
            df = df.loc[df["MetaCohort"] == cohort, :]
        return dict(zip(df.loc[:, key], df.loc[:, value]))

    @staticmethod
    def load_data(filepath, profile_genes, trans_dict, sample_dict):
        selection = []
        data = []
        columns = []
        indices = []

        print("\tLoading expression matrix")
        with gzip.open(filepath, 'rb') as f:
            for i, line in enumerate(f):
                if (i == 0) or (i % 1000 == 0):
                    print("\t\tfound {}/{} genes".format(len(data),
                                                         len(profile_genes)))

                splitted_line = np.array(line.decode().split('\t'))
                if i == 0:
                    for j, col in enumerate(splitted_line):
                        if col in sample_dict.keys():
                            selection.append(j)
                            columns.append(col)
                    if len(selection) <= 0:
                        break

                gene = splitted_line[0]
                if gene in trans_dict.keys() and trans_dict[gene] in profile_genes and trans_dict[gene] not in indices:
                    indices.append(trans_dict[gene])
                    data.append([float(x) for x in splitted_line[selection]])
        f.close()

        return pd.DataFrame(data, index=indices, columns=columns)

    def save(self):
        print("Saving files")
        if self.signature is not None:
            self.signature.to_csv(self.signature_file, compression="gzip", sep="\t", header=True, index=True)
            print("\tsaved dataframe: {} "
                  "with shape: {}".format(os.path.basename(self.signature_file),
                                          self.signature.shape))

        if self.expression is not None:
            self.expression.to_csv(self.expression_file, compression="gzip", sep="\t", header=True, index=True)
            print("\tsaved dataframe: {} "
                  "with shape: {}".format(os.path.basename(self.expression_file),
                                          self.signature.shape))

    def settings_match(self):
        with open(self.settings_file) as f:
            try:
                prev_settings = json.load(f)
            except json.decoder.JSONDecodeError:
                return False
        f.close()
        if (prev_settings["data_path"] == self.data_path) and \
            (prev_settings["signature_path"] == self.signature_path) and \
            (prev_settings["translate_path"] == self.translate_path) and \
            (prev_settings["sample_path"] == self.sample_path) and \
            (prev_settings["cohort"] == self.cohort):
            return True

        return False

    def load_saved_files(self):
        print("\tLoading signature matrix")
        self.signature = pd.read_csv(self.signature_file,
                                     sep="\t",
                                     header=0,
                                     index_col=0)
        print("\tloaded dataframe: {} "
              "with shape: {}".format(os.path.basename(self.signature_file),
                                      self.signature.shape))

        print("\tLoading expression matrix")
        self.expression = pd.read_csv(self.expression_file,
                                     sep="\t",
                                     header=0,
                                     index_col=0)
        print("\tloaded dataframe: {} "
              "with shape: {}".format(os.path.basename(self.expression_file),
                                      self.expression.shape))

    def load_ground_truth(self):
        print("\tLoading ground truth matrix")
        self.ground_truth = pd.read_csv(self.ground_truth_path,
                                        sep="\t",
                                        header=0,
                                        index_col=0)
        print("\tloaded dataframe: {} "
              "with shape: {}".format(os.path.basename(self.ground_truth_path),
                                      self.ground_truth.shape))

    def get_signature(self):
        return self.signature

    def get_expression(self):
        return self.expression

    def get_ground_truth(self):
        return self.ground_truth

    def get_info_per_celltype(self):
        if self.ground_truth is None:
            return {}
        means = self.ground_truth.mean(axis=0).to_dict()
        stds = self.ground_truth.std(axis=0).to_dict()

        info = {}
        for key in means.keys():
            info[key] = (means[key], stds[key])
        return info

    def print_info(self):
        print("Signature matrix:\t{} rows and {} columns".format(self.signature.shape[0], self.signature.shape[1]))
        print("Expression matrix:\t{} rows and {} columns".format(self.expression.shape[0], self.expression.shape[1]))
        if self.ground_truth is not None:
            print("Ground truth matrix:\t{} rows and {} columns".format(self.ground_truth.shape[0], self.ground_truth.shape[1]))
            print("Average fraction per celltype:")
            for celltype, (mean, std) in self.get_info_per_celltype().items():
                print("\t{:20s}: mean = {:.2f} std = {:.2f}".format(celltype,
                                                                    mean, std))
        print("")
