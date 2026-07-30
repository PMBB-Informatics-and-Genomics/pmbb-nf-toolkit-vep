#!/usr/bin/env python3

import argparse
import sys
import yaml
import pandas as pd

DEFAULTS = {
    'gnomad_af_col': 'gnomADe_AF',
    'cadd_col': 'CADD_PHRED',
    'cadd_raw_col': 'CADD_RAW',
    'lof_col': 'LoF',
    'consequence_col': 'Consequence',
    'revel_col': 'REVEL_score',
    'spliceai_pred_col': 'SpliceAI_pred',
    'revel_threshold': 0.773,
    'cadd_threshold': 28.1,
    'spliceai_threshold': 0.2,
    'gnomad_af_threshold': 0.01,
}


def get_args():
    p = argparse.ArgumentParser(description='Generate BRaVa annotations and SAIGE group files from VEP output')
    p.add_argument('--input_tsv', required=True, help='Merged VEP annotations TSV (from merge_batches)')
    p.add_argument('--output_prefix', required=True, help='Batch name used to name output files')
    p.add_argument('--config', required=True, help='Path to vep_plugins.yaml')
    p.add_argument('--output_dir', default='.', help='Output directory (default: current dir)')
    return p.parse_args()


def load_config(config_path):
    with open(config_path) as f:
        full = yaml.safe_load(f)
    cfg = dict(DEFAULTS)
    if full.get('group_files'):
        cfg.update(full['group_files'])
    return cfg


def make_new_annotations(input_tsv, cfg):
    gnomad_af_col = cfg['gnomad_af_col']
    cadd_col = cfg['cadd_col']
    cadd_raw_col = cfg['cadd_raw_col']
    lof_col = cfg['lof_col']
    consequence_col = cfg['consequence_col']
    revel_col = cfg['revel_col']
    spliceai_pred_col = cfg['spliceai_pred_col']
    revel_threshold = float(cfg['revel_threshold'])
    cadd_threshold = float(cfg['cadd_threshold'])
    spliceai_threshold = float(cfg['spliceai_threshold'])
    gnomad_af_threshold = float(cfg['gnomad_af_threshold'])

    dup_drop_cols = ['Uploaded_variation', 'Gene', gnomad_af_col, lof_col,
                     consequence_col, revel_col, cadd_col, spliceai_pred_col]
    dup_drop_cols_present = None  # resolved after first chunk

    chunks = []
    before_genes = set()
    after_genes = set()

    for chunk in pd.read_table(input_tsv, sep='\t', low_memory=False, chunksize=500_000):
        chunk = chunk.mask(chunk == '-')
        chunk['Uploaded_variation'] = chunk['#Uploaded_variation']
        chunk = chunk.dropna(subset=['Gene'])
        before_genes.update(chunk['Gene'])

        mane_filter = ~pd.isnull(chunk['MANE_SELECT'])
        canonical_filter = (chunk['CANONICAL'] == 'YES') & pd.isnull(chunk['MANE_SELECT'])
        chunk = chunk[mane_filter | canonical_filter]
        after_genes.update(chunk['Gene'])

        chunk = chunk[chunk['BIOTYPE'] == 'protein_coding']

        if dup_drop_cols_present is None:
            dup_drop_cols_present = [c for c in dup_drop_cols if c in chunk.columns]

        chunks.append(chunk)
        del chunk

    dropped_genes = before_genes - after_genes
    print(f'Gene IDs before filter: {len(before_genes)}')
    print(f'Gene IDs after MANE/CANONICAL filter: {len(after_genes)}')
    print(f'Dropped genes: {len(dropped_genes)}')

    df = pd.concat(chunks, ignore_index=True)
    del chunks

    print(f'Rows before dedup: {len(df):,}')
    df = df.drop_duplicates(subset=dup_drop_cols_present)
    print(f'Rows after dedup: {len(df):,}')

    df = df.set_index(['Uploaded_variation', 'Gene'])

    check_dup = df[df.index.duplicated(keep=False)]
    if len(check_dup) > 0:
        print(check_dup)
        sys.exit('ERROR: Duplicate (variant, gene) pairs after filtering.')
    del check_dup

    df[revel_col] = df[revel_col].apply(
        lambda x: max((float(v) for v in str(x).split(',') if v not in ('.', '')), default=float('nan'))
        if pd.notna(x) else x
    )

    float_cols = [c for c in [cadd_raw_col, cadd_col, gnomad_af_col] if c in df.columns]
    df[float_cols] = df[float_cols].astype(float)

    # Parse SpliceAI; if column absent treat spliceai_ds as all-NaN
    if spliceai_pred_col in df.columns:
        splice = df[spliceai_pred_col].str.split(pat='|', expand=True)
        splice.columns = ['symbol', 'DS_AG', 'DS_AL', 'DS_DG', 'DS_DL',
                          'DP_AG', 'DP_AL', 'DP_DG', 'DP_DL']
        splice = splice.mask(splice == 'None')
        ds_cols = ['DS_AG', 'DS_AL', 'DS_DG', 'DS_DL']
        splice[ds_cols + ['DP_AG', 'DP_AL', 'DP_DG', 'DP_DL']] = \
            splice[ds_cols + ['DP_AG', 'DP_AL', 'DP_DG', 'DP_DL']].astype(float)
        splice['spliceai_ds'] = splice[ds_cols].max(axis=1)
    else:
        splice = pd.DataFrame(index=df.index)
        splice['spliceai_ds'] = float('nan')

    brava_annots = pd.Series(dtype='str', index=df.index)

    # Synonymous
    syn_consequence = df[consequence_col].str.contains('synonymous_variant', na=False)
    syn_splice = (splice['spliceai_ds'] < spliceai_threshold) | pd.isna(splice['spliceai_ds'])
    brava_annots.loc[df.index[syn_consequence & syn_splice]] = 'synonymous'

    # Missense-type consequences
    is_missense = df[consequence_col].str.contains('missense_variant', na=False)
    is_start_loss = df[consequence_col].str.contains('start_lost', na=False)
    is_stop_loss = df[consequence_col].str.contains('stop_lost', na=False)
    is_inframe_ins = df[consequence_col].str.contains('inframe_insertion', na=False)
    is_inframe_del = df[consequence_col].str.contains('inframe_deletion', na=False)
    is_splice = df[consequence_col].str.contains('splice_', na=False)
    missense_consequence = is_missense | is_start_loss | is_stop_loss | is_inframe_ins | is_inframe_del | is_splice

    brava_annots.loc[df.index[missense_consequence]] = 'other_missense'

    # Damaging missense
    dm_revel = df[revel_col] >= revel_threshold
    dm_cadd = df[cadd_col] >= cadd_threshold if cadd_col in df.columns else pd.Series(False, index=df.index)
    dm_splice = splice['spliceai_ds'] >= spliceai_threshold
    dm_score = dm_revel | dm_cadd | dm_splice
    lc_loftee = df[lof_col] == 'LC'
    dm_mask = (missense_consequence & dm_score) | lc_loftee
    brava_annots.loc[df.index[dm_mask]] = 'damaging_missense'

    # pLoF
    splicing = df[is_splice].copy()
    splicing['Consequence_List'] = splicing[consequence_col].str.split(pat=',')
    not_only_splice_filter = splicing['Consequence_List'].apply(
        lambda x: any('splice_' not in e for e in x)
    )
    not_only_splice_idx = splicing.index[not_only_splice_filter]
    not_any_splice = ~is_splice
    only_splice = ~df.index.isin(not_only_splice_idx) & is_splice
    not_only_splice = df.index.isin(not_only_splice_idx)
    hc_plof = df[lof_col] == 'HC'
    plof_mask = hc_plof & (not_any_splice | (only_splice & dm_splice) | not_only_splice)
    brava_annots.loc[df.index[plof_mask]] = 'pLoF'

    too_common = df[gnomad_af_col] > gnomad_af_threshold if gnomad_af_col in df.columns else pd.Series(False, index=df.index)
    brava_annots = brava_annots.mask(too_common)

    if spliceai_pred_col in df.columns:
        df = pd.concat([df, splice], axis=1)
    df.insert(0, 'annotation', brava_annots)

    need_cols = [c for c in ['SYMBOL', 'annotation', gnomad_af_col, lof_col, consequence_col,
                              revel_col, cadd_col, 'spliceai_ds', spliceai_pred_col]
                 if c in df.columns or c == 'annotation']

    print(f'Final annotated rows: {len(df):,}')
    return df[need_cols], dropped_genes


def write_group_file(annot_df, output_prefix, output_dir):
    out_path = f'{output_dir}/{output_prefix}.saige_group_file.txt'
    annot_df = annot_df.dropna(subset=['annotation'])
    print(f'Genes with annotations: {len(annot_df.index.get_level_values("Gene").unique())}')

    gene_groups = pd.DataFrame(dtype=str, columns=['values'])
    annot_groups = pd.DataFrame(dtype=str, columns=['values'])

    for gene, sub_df in annot_df.groupby(level='Gene'):
        check_dup = sub_df[sub_df.index.duplicated(keep=False)]
        if len(check_dup) > 0:
            print(check_dup)
            sys.exit(f'ERROR: Duplicates in gene {gene}')
        variant_ids = sub_df.index.get_level_values('Uploaded_variation')
        gene_groups.loc[gene, 'values'] = '\t'.join(variant_ids)
        annot_groups.loc[gene, 'values'] = '\t'.join(sub_df['annotation'])

    gene_groups['row_type'] = 'var'
    annot_groups['row_type'] = 'anno'
    all_groups = (pd.concat([gene_groups, annot_groups])
                  .sort_values(by='row_type', ascending=False)
                  .sort_index(kind='stable'))

    with open(out_path, 'w') as f:
        for gene, row in all_groups.iterrows():
            f.write(f"{gene}\t{row['row_type']}\t{row['values']}\n")

    print(f'Wrote group file: {out_path}')


def main():
    args = get_args()
    cfg = load_config(args.config)

    annot_df, dropped_genes = make_new_annotations(args.input_tsv, cfg)

    brava_out = f'{args.output_dir}/{args.output_prefix}.brava_annotations.tsv'
    annot_df.to_csv(brava_out, sep='\t')
    print(f'Wrote BRaVa annotations: {brava_out}')

    dropped_out = f'{args.output_dir}/{args.output_prefix}.dropped_genes.txt'
    with open(dropped_out, 'w') as f:
        f.write('\n'.join(sorted(dropped_genes)))
    print(f'Wrote dropped genes: {dropped_out}')

    write_group_file(annot_df, args.output_prefix, args.output_dir)


if __name__ == '__main__':
    main()
