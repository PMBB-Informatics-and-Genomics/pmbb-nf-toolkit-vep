import argparse
import pandas as pd
# from distutils.version import StrictVersion

def get_args():
    parser = argparse.ArgumentParser(description=".")
    # Modified to accept multiple file arguments or a single string with space-separated files
    parser.add_argument("-i", "--input_file_list", required=True, 
                       help="space-separated list of input files to merge OR path to file containing list")
    parser.add_argument("-o", "--output_file", required=True, 
                       help="output file for merged annotations")
    parser.add_argument("--direct_files", action="store_true", 
                       help="treat input_file_list as direct file paths rather than a file containing paths")
    return parser

def file2list(infile):
    """Read a newline-separated file, remove \n and return a list"""
    with open(infile, "r") as myfile:
        outlist = [item.rstrip() for item in myfile.readlines()]
    return outlist

def parse_input_files(input_arg, direct_files=False):
    """Parse input files from either a file list or direct arguments"""
    if direct_files:
        # Split space-separated file paths
        return input_arg.split()
    else:
        # Try to determine if it's a file path or space-separated files
        if len(input_arg.split()) == 1 and input_arg.endswith('.txt'):
            # Single argument ending in .txt - treat as file path
            return file2list(input_arg)
        else:
            # Multiple arguments or doesn't look like a file path - treat as direct files
            return input_arg.split()

args = get_args().parse_args()
input_file_list_arg = args.input_file_list
output_file = args.output_file

# get list, parse input files
input_file_list = parse_input_files(input_file_list_arg, args.direct_files)
print(f"\nFound {len(input_file_list)} files")
print(f"Files to process: {input_file_list}")

# instance of empty dictionary to hold dataframes
dfs = {}
for file in input_file_list:
    print(f"\nReading in {file}")
    try:
        df = pd.read_table(file, low_memory=False)
        dfs[file] = df
    except Exception as e:
        print(f"Error reading {file}: {e}")
        sys.exit(1)
    
# combine
print(f"\ncombining all vep files")
bigdf = pd.concat(dfs,axis='index',ignore_index=True)
bigdf[['chromosome','bp_location']] = bigdf['Location'].str.split(':', n=1, expand=True)
bigdf["chromosome"] = bigdf["chromosome"].str.replace("chr", "")

# sort values
print(f"\nSorting the Dataframe")
bigdf_sorted = bigdf.sort_values(by=['chromosome','bp_location','Gene', 'Feature'],ignore_index=True)

# drop unnamed columns
bigdf_sorted.drop(bigdf.filter(regex='Unnamed').columns, axis=1, errors='ignore',inplace=True)

# sort columns: core VEP columns first in canonical order, then plugin-specific alphabetically.
# safety net for chunks that were missing columns (NaN-filled by outer join) ending up in
# unpredictable positions after concat.
CORE_VEP_COLS = [
    '#Uploaded_variation', 'Location', 'Allele', 'Gene', 'Feature',
    'Feature_type', 'Consequence', 'cDNA_position', 'CDS_position',
    'Protein_position', 'Amino_acids', 'Codons', 'Existing_variation',
    'HGVSc', 'HGVSp', 'chromosome', 'bp_location',
]
current_cols = bigdf_sorted.columns.tolist()
pinned = [c for c in CORE_VEP_COLS if c in current_cols]
plugin_cols = sorted([c for c in current_cols if c not in CORE_VEP_COLS])
bigdf_sorted = bigdf_sorted[pinned + plugin_cols]

# write to combined file
bigdf_sorted.to_csv(output_file,sep='\t',index=False)
print("\nComplete")