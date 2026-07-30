// modules/download_vep_cache.nf

nextflow.enable.dsl = 2

process download_vep_cache {
    errorStrategy 'terminate'

    output:
        val "ready", emit: status
    script:
        """
        echo "Downloading VEP fasta and cache..."
        mkdir -p ${params.vep_data_directory}
        if ! INSTALL.pl \\
            -c /vep_cache \\
            -a cf \\
            -s homo_sapiens \\
            -y GRCh38; then
            
            echo "ERROR: Automatic Download of VEP cache failed. Please manually download the cache for Homo_sapiens GRCh38. See: https://useast.ensembl.org/info/docs/tools/vep/script/vep_cache.html#cache for more info." >&2
            exit 1
        fi
        """
    stub:
        """
        echo "ready"
        """
} 