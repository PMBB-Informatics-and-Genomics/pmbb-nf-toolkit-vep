// modules/run_vep_plugin.nf

nextflow.enable.dsl = 2

process run_vep_plugin {
    // container options
    // container "${params.vep_sif}"
    // containerOptions "-B ${params.vep_data_directory}:/vep_cache/"
    // singularity.enabled = true
    publishDir "${params.output_directory ?: launchDir}/results_byChunk_byPlugin/"
    tag "${chunk}.${plugin_name}"

    input:
        tuple val (input_directory), val(input_prefix), val(chunk), val(suffix), val(plugin_name)
        val cpu

    output:
        // tuple val(input_prefix), val(chunk), output_file_name
        tuple val(input_prefix), val(chunk), path("${input_prefix}${chunk}.${plugin_name}.tsv", optional: true)
        // path(output_file_name: new File("${input_prefix}").getName() + "${chunk}.${plugin_name}.tsv")
        // path "*${chunk}.${plugin_name}.tsv", optional: true
        // path "${input_prefix}${chunk}.${plugin_name}.tsv", optional: true

    script:
        // Parse the plugins config to get plugin details
        def pluginsConfig = new groovy.yaml.YamlSlurper().parse(new File(params.plugins_config_file))
        def plugins = pluginsConfig.plugins
        def plugin = plugins[plugin_name]
        def vep_data_directory = (params.vep_data_directory ?: pluginsConfig.vep_data_directory) as String

        // Skip if plugin is not enabled or does not exist
        if (!plugin || !plugin.enabled) {
            """
            echo "Plugin ${plugin_name} is not enabled or does not exist. Skipping."
            """
            exit(0)
        }
        else {
            def topVars = [
                vep_data_directory: vep_data_directory
            ]

            // Interpolate top-level vars in ref_fasta
            def ref_fasta = pluginsConfig.ref_fasta as String
            topVars.each { k, v -> ref_fasta = ref_fasta.replace("\${${k}}", v) }

            // Interpolate top-level vars in plugin variables
            def resolvedVars = [:]
            plugin.variables.each { k, v ->
                def val = v as String
                topVars.each { tk, tv -> val = val.replace("\${${tk}}", tv) }
                resolvedVars[k] = val
            }

            // Then interpolate top-level vars and plugin vars in command
            def command = plugin.command as String
            topVars.each { k, v -> command = command.replace("\${${k}}", v) }
            resolvedVars.each { k, v ->
                command = command.replace("\${${k}}", v)
            }


            def input_file_path = "${input_directory}/${input_prefix}${chunk}${suffix}"
            // def input_file_name = new File(input_file_path).getName()
            def output_file_name = new File(input_prefix).getName() + "${chunk}.${plugin_name}.tsv"

            """
            echo "Running VEP plugin ${plugin_name} on chunk ${chunk}"
            echo "Input file: ${input_file_path}"
            echo "VEP command: ${command}"

            vep \\
                -i "${input_file_path}" \\
                -o "${output_file_name}" \\
                --dir_cache "${vep_data_directory}" \\
                --cache \\
                --offline \\
                --format vcf \\
                --force_overwrite \\
                --tab \\
                --buffer_size 5000 \\
                --fork ${cpu} \\
                --no_escape \\
                --hgvs \\
                --fasta ${ref_fasta} \\
                ${command}
            """
        }

    stub:
        """
        touch "${input_prefix}${chunk}.${plugin_name}.tsv"
        """
}
