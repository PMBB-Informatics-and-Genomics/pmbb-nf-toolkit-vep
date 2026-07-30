// modules/merge_batches.nf

nextflow.enable.dsl = 2

process merge_batches {
    // container options
    container = ''
    publishDir "${params.output_directory ?: launchDir}/results_byBatch/"
    label 'highmem'
    errorStrategy 'retry'
    maxRetries 3
    // needs dynamic memory {} allocation based on input file sizes and attempt number for retries
    memory {
        def fileSizeGb = input_files.collect { it.size() }.sum() / (1024**3)
        def max_mem_gb = 256
        def baseMemGb = Math.max(16, (Math.ceil(fileSizeGb) + 4).toLong())
        def attempt_mem = Math.min(baseMemGb, max_mem_gb)
        return attempt_mem.GB
    }

    input:
    tuple val(batch), path(input_files)

    output:
    path("${batch}.vep_annotations.tsv")

    script:
    def output_file = "${batch}.vep_annotations.tsv"

    // // let's explicitly handle file lists
    // def files_string
    // if (input_files instanceof Collection) {
    //     files_string = input_files.join(' ')
    // } else if (input_files instanceof List) {
    //     files_string = input_files.join(' ')
    // } else {
    //     files_string = input_files.toString()
    // }

    """
    ${params.python} ${projectDir}/bin/vep_chunks_to_batches.py \\
        --input_file_list "${input_files.join(' ')}" \\
        --output_file ${output_file} \\
        --direct_files
    """

    stub:
    def output_file = "${batch}.vep_annotations.tsv"
    """
    touch "${output_file}"
    """
}