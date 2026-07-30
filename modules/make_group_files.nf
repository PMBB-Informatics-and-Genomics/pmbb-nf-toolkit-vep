// modules/make_group_files.nf

nextflow.enable.dsl = 2

process make_group_files {
    container = ''
    publishDir "${params.output_directory ?: launchDir}/results_byBatch_groupFiles/"
    tag "${batch}.group_files"
    label 'highmem'

    memory {
        def fileSizeGb = input_tsv.size() / (1024**3)
        def max_mem_gb = 128
        def baseMemGb = Math.max(16, (Math.ceil(fileSizeGb) * 4 + 4).toLong())
        def attempt_mem = Math.min(baseMemGb, max_mem_gb)
        return attempt_mem.GB
    }

    input:
    tuple val(batch), path(input_tsv)
    path(plugins_config_file)

    output:
    tuple val(batch),
          path("${batch}.brava_annotations.tsv"),
          path("${batch}.saige_group_file.txt"),
          path("${batch}.dropped_genes.txt")

    script:
    """
    ${params.python} ${projectDir}/bin/make_group_files.py \\
        --input_tsv "${input_tsv}" \\
        --output_prefix "${batch}" \\
        --config "${plugins_config_file}" \\
        --output_dir "."
    """

    stub:
    """
    touch "${batch}.brava_annotations.tsv"
    touch "${batch}.saige_group_file.txt"
    touch "${batch}.dropped_genes.txt"
    """
}
