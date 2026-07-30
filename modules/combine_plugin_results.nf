// modules/combine_plugin_results.nf

nextflow.enable.dsl = 2

process combine_plugin_results {
    // container options
    container = ''
    publishDir "${params.output_directory ?: launchDir}/results_byChunk/"
    tag "${chunk}.combined_results"
    label 'highmem'
    errorStrategy 'retry'
    maxRetries 3
    // needs dynamic memory {} allocation based on input file sizes and attempt number for retries
    memory {
        def fileSizeGb = plugin_results.collect { it.size() }.sum() / (1024**3)
        def max_mem_gb = 256
        def baseMemGb = Math.max(16, (Math.ceil(fileSizeGb) + 4).toLong())
        def attempt_mem = Math.min(baseMemGb, max_mem_gb)
        return attempt_mem.GB
    }

    input:
    tuple val(input_prefix), val(chunk), path(plugin_results)

    output:
    tuple val(input_prefix), val(chunk), path("${input_prefix}${chunk}.vep_annotations.tsv")

    // def input_prefix_path = "${input_prefix}${chunk}"
    // def file_prefix = "${input_prefix}${chunk}.${suffix}"

    script:
    
    def input_prefix_basename = new File("${input_prefix}").getName()

    """
    echo "Combining plugin results for chunk ${chunk} from input prefix ${input_prefix}"
    ${params.python} ${projectDir}/bin/combine_plugin_results.py \\
        --input_prefix "${input_prefix}${chunk}" \\
        --input_file_list ${plugin_results.join(' ')}
    """

    stub:
    """
    touch "${input_prefix}${chunk}.vep_annotations.tsv"
    """
}