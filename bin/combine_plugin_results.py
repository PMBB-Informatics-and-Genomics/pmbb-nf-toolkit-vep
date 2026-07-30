#!/usr/bin/env python

import argparse
import csv
import glob
import os
from pathlib import Path
import pandas as pd

def get_args():
    parser = argparse.ArgumentParser(description=".")
    # required
    # Optional argument which requires a parameter (eg. -n project_name)
    parser.add_argument("-i", "--input_file_list", nargs='+', required=False, help="input file list of vep files to combine")
    # parser.add_argument("-i", "--input_file", required=True, help="input vcf file used for VEP")
    parser.add_argument("-p", "--input_prefix", required=True, help="input prefix for vep files to combine")
    # parser.add_argument("-d", "--input_directory", required=True, help="input directory where plugin-level VEP annotations are located, all files in here will be concatenated, so if there are already some combined files, they will be replicated in the concatenation")
    # parser.add_argument("-o", "--output_directory", required=True, help="output directory for combined VEP annotations, can be same as input_directory, files will be appended with .vep_annotations.tsv")
    # parser.add_argument("-s", "--suffix", required=False, help="suffix to remove from input file name, if not provided, will remove last extension")
    return(parser)

def extract_filename(file_string, suffixes=None):
    """
    Extracts the filename from a file string, optionally removing a specific suffix.

    Args:
        file_string: The full file string with path and suffix.
        suffixes: The suffixes to remove. Must be a list. If None, removes the last extension.

    Returns:
        The filename without path and the specified suffix (or last extension).
    """
    base = os.path.basename(file_string)  # Get the filename with suffix
    if suffixes:
        for suffix in suffixes:
            if base.lower().endswith(suffix.lower()):
                base = base[:-len(suffix)] # Remove the specified suffix
                break # exit loop after removing first match
    else:
        base = os.path.splitext(base)[0]  # Remove the last extension
    return base

def get_basename(filepath, parent=False, suffixes=None):
    """
    Takes a path (string or PosixPath object) and returns the filename without path or suffix.

    Args:
        filepath (filepath): filepath to operate on
        parent (bool, optional): Whether to keep parent path in name. Defaults to False.
        suffixes (list, optional): list of suffixes to strip (.txt, .csv), otherwise strips anything after last period. Defaults to None.

    Returns:
        str: stripped filename
    """
    filename = Path(filepath)
    # if suffixes supplied, only strip those
    if suffixes:
        while filename.suffix in set(suffixes):
            filename = filename.with_suffix("")
    else:
        filename = filename.with_suffix("")
    # if parent set to true, keep it
    if parent:
        filename = str(filename)
    else:
        filename = filename.name
    return filename


def find_matching_files(prefix, suffix):
  """
  Finds all files matching a given prefix and suffix.

  Args:
    prefix: The prefix string, including the path and partial filename.
    suffix: The suffix string.

  Returns:
    A list of matching filenames.
  """
  return glob.glob(f"{prefix}*{suffix}")

def read_vep_tables(infile):
    tempfile = f"{infile}.tmp"
    with open(infile, 'r') as infile, open(tempfile, 'w', newline='') as outfile:
        reader = csv.reader(infile, delimiter='\t')
        writer = csv.writer(outfile, delimiter='\t')
        for row in reader:
            if not row[0].startswith('##'):
                writer.writerow(row)
    df = pd.read_csv(tempfile, sep='\t')
    df['variant_feature'] = df['#Uploaded_variation'] + '.' + df['Feature']
    df.set_index('variant_feature', inplace=True)
    os.remove(tempfile)
    return df

def read_vep_tables_2(infile, set_index=False):
    colnames = None
    table_file = open(infile)
    line = next(table_file)
    while colnames is None:
        if line[:2] != '##':
            colnames = line.split()       
        line = next(table_file)

    df = pd.read_csv(infile, sep='\t', low_memory=False, names=colnames, comment='#', header=None)
    df = df.drop_duplicates()
    
    if set_index:
        df['variant_feature'] = df['#Uploaded_variation'] + '.' + df['Feature']
        df.set_index('variant_feature', inplace=True)
    # os.remove(tempfile)
    return df


args = get_args().parse_args()
input_file_list = args.input_file_list
input_prefix = args.input_prefix
output_file = f"{input_prefix}.vep_annotations.tsv"

# instance of empty dictionary to hold dataframes
dfs = {}
for file in input_file_list:
    print(f"\nReading in {file}...")
    # df = read_vep_tables(file)
    df = read_vep_tables_2(file, set_index=True)
    dfs[file] = df
    

# combine
print(f"\ncombining all vep files...")
bigdf = pd.concat(dfs,axis='columns')

# Get the column index values for the specified levels
index_values = bigdf.columns.get_level_values(1)

# Remove duplicate column names based on the selected level
print(f"\nDeDuplicating columns...")
dedupe = bigdf.loc[:, ~index_values.duplicated()].droplevel(axis=1,level=0)

# reorder columns so it matches vep analyses
cols = dedupe.reset_index().columns.tolist()
column_order = cols[1:] + cols[:1]
dedupe = dedupe.reset_index()[column_order]

# sort columns: core VEP columns first in canonical order, then plugin-specific alphabetically,
# variant_feature (index) last
CORE_VEP_COLS = [
    '#Uploaded_variation', 'Location', 'Allele', 'Gene', 'Feature',
    'Feature_type', 'Consequence', 'cDNA_position', 'CDS_position',
    'Protein_position', 'Amino_acids', 'Codons', 'Existing_variation',
    'HGVSc', 'HGVSp',
]
current_cols = dedupe.columns.tolist()
pinned = [c for c in CORE_VEP_COLS if c in current_cols]
tail = [c for c in current_cols if c == 'variant_feature']
plugin_cols = sorted([c for c in current_cols if c not in CORE_VEP_COLS and c != 'variant_feature'])
dedupe = dedupe[pinned + plugin_cols + tail]

# write to combined file
print(f"\nWriting output file to {output_file}")
dedupe.to_csv(output_file,sep='\t',index=False)
print("\nComplete")