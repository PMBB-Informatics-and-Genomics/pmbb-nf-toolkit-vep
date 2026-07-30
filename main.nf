#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

import groovy.yaml.YamlSlurper

params.input_directory     = params.input_directory     ?: "${launchDir}/Input"              // directory containing input VCF files
params.input_prefix        = params.input_prefix        ?: 'chromosome_'                     // filename prefix before chunk identifier
params.input_suffix        = params.input_suffix        ?: '.info.vcf.gz'                    // filename suffix/extension after chunk identifier
params.chunks_file         = params.chunks_file         ?: "${launchDir}/Input/chromosome_list.txt" // file listing chunks (e.g. chromosome numbers) to process
params.batches_file        = params.batches_file        ?: "${launchDir}/Input/batches.tsv"  // TSV mapping batches to chunks for final merging
params.output_directory    = params.output_directory    ?: "${launchDir}/plugin_chunk_results" // root output directory for all results
params.cpu                 = params.cpu                 ?: 1                                 // number of CPUs (VEP --fork) per plugin job
params.plugins_config_file = params.plugins_config_file ?: "${launchDir}/vep_plugins.yaml"  // YAML file defining VEP plugins and their settings
params.vep_sif             = params.vep_sif             ?: null                              // path to VEP Singularity image file
params.vep_data_directory  = params.vep_data_directory  ?: "${launchDir}/vep_data"           // path to VEP cache/data directory (bound into container)
params.download_vep_cache  = params.download_vep_cache  ?: false                             // set true to download VEP cache before running
params.python              = params.python              ?: 'python'                             // path to python3 executable (override if container default is python2)
params.make_group_files    = params.make_group_files    ?: false                             // set true to generate BRaVa annotations and SAIGE group files

include { run_vep_plugin } from './modules/run_vep_plugin'
include { combine_plugin_results } from './modules/combine_plugin_results'
include { merge_batches } from './modules/merge_batches'
include { download_vep_cache } from './modules/download_vep_cache'
include { make_group_files } from './modules/make_group_files'

workflow {
    log.info("Starting VEP plugin run with the following parameters:")
    log.info(String.format("%-25s : %s", "Run as", workflow.commandLine))
    log.info(String.format("%-25s : %s", "Run location", launchDir))
    log.info(String.format("%-25s : %s", "Started at", workflow.start))
    log.info(String.format("%-25s : %s", "Input directory", params.input_directory))
    log.info(String.format("%-25s : %s", "Input prefix", params.input_prefix))
    log.info(String.format("%-25s : %s", "Output directory", params.output_directory))
    log.info(String.format("%-25s : %s", "CPU", params.cpu))
    log.info(String.format("%-25s : %s", "Plugins config", params.plugins_config_file))
    log.info(String.format("%-25s : %s", "VEP SIF", params.vep_sif))
    log.info(String.format("%-25s : %s", "VEP data", params.vep_data_directory))
    log.info(String.format("%-25s : %s", "Chunks file", params.chunks_file))
    log.info(String.format("%-25s : %s", "InputSuffix", params.input_suffix))
    log.info(String.format("%-25s : %s", "Batches file", params.batches_file))
    log.info(String.format("%-25s : %s", "Download VEP cache", params.download_vep_cache))
    log.info(String.format("%-25s : %s", "Python executable", params.python))
    log.info(String.format("%-25s : %s", "Make group files", params.make_group_files))
    if (params.download_vep_cache) {
        log.info("Downloading VEP cache and fasta files...")
        cache_ready = download_vep_cache()
    } else {
        log.info("Skipping VEP cache download as per configuration.")
        cache_ready = Channel.of("ready")
    }

    // Read chunks from the file or use predefined Groovy list
    chunks = file(params.chunks_file).readLines() ?: [22] // default 22
    // Read the plugins config file and parse it
    def plugins_config_file = file(params.plugins_config_file)
    def pluginsConfig = new groovy.yaml.YamlSlurper().parse(plugins_config_file)
    // Get the list of enabled plugin names
    def VEPplugins = pluginsConfig.plugins.findAll { name, config ->
        config.enabled == true
    }.keySet() as List
    // log.info("Enabled plugins: ${VEPplugins.join(', ')}")
    log.info(String.format("%-25s : %s", "Enabled plugins", VEPplugins.join(', ')))
    chunks = Channel.from(chunks) // create base channel from chunks
    plugins = Channel.from(VEPplugins) // create base channel from plugins
    // create chunks plugin combinations
    // // old version without cache_ready gates
    // chunks
    //     .combine(plugins)
    //     .map { chunk, plugin ->
    //             new Tuple(params.input_directory, params.input_prefix, chunk, params.input_suffix, plugin)
    //         }
    //     .set { chunks_plugins_channel }
    // new version with cache_ready gating
    chunks
        .combine(plugins)
        .combine(cache_ready) // This gates execution until cache is ready
        .map { chunk, plugin, ready ->
           new Tuple(params.input_directory, params.input_prefix, chunk, params.input_suffix, plugin)
        }
        .set { chunks_plugins_channel }

    // Run the VEP plugin for each chunk and plugin combination
    chunk_plugin_results = run_vep_plugin(
        chunks_plugins_channel,
        params.cpu
    )

    // group channel by chunk to collect all outputs for each chunk
    chunk_plugin_results
        .map { input_prefix, chunk, file -> 
            // Restructure the tuple to group by input_prefix and chunk
            return tuple(tuple(input_prefix, chunk), file)
        }
        .groupTuple()
        .map { key, files -> 
            // Unpack the grouped key back to individual values
            def (input_prefix, chunk) = key
            // force files to be a list even if only one file
            return tuple(input_prefix, chunk, [files].flatten())
        }
        .set { chunk_plugin_results_grouped }

    // Combine the plugin results for each chunk
    // This will create a channel of tuples: (input_prefix, chunk, combined_results.tsv)
    plugin_results_combined = combine_plugin_results(chunk_plugin_results_grouped)

    // Create a channel to contain each unique batch in the batches_file
    Channel
        .fromPath(params.batches_file)
        .splitCsv(header: false, sep: '\t', strip: true)
        .map { row -> 
            def (batch, chunk) = row
            [batch, chunk]
        }
        .groupTuple() // Group chunks by first element - batch: [batch, [chunk1, chunk2, ...]]
        .set { batches_channel }
    // // Debug output
    // batches_channel.view { batch, chunk_list -> "Batch: ${batch}, Chunks: ${chunk_list}" }

    // Create cross product and filter for matching chunks
    batched_results_channel = plugin_results_combined
        .combine(batches_channel)
        .filter { input_prefix, chunk, file, batch, chunk_list ->
            // Keep only if the chunk is in the chunk_list for the batch
            chunk_list.contains(chunk as String)
        }
        .map { input_prefix, chunk, file, batch, chunk_list ->
            [batch, file]
        }
        .groupTuple()
    
    // merge batches
    final_merged_results = merge_batches(batched_results_channel)

    // Optionally generate BRaVa annotations and SAIGE group files
    if (params.make_group_files) {
        // merge_batches emits only path; recover batch name from filename
        group_files_input = final_merged_results
            .map { tsv_file ->
                def batch = tsv_file.name.replace('.vep_annotations.tsv', '')
                tuple(batch, tsv_file)
            }
        make_group_files(group_files_input, file(params.plugins_config_file))
    }
}