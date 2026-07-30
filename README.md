
Documentation for VEP
=====================

# Module Overview


**Ensembl VEP predicts the effect of your variants** (SNPs, insertions, deletions, CNVs or structural variants) on gene transcripts and protein sequence, as well as regulatory regions. It reports reference data including gene and variant phenotype associations and population allele frequencies to facilitate variant prioritization and interpretation. This pipeline works blazingly fast by parallelizing across plugins and chunks of Input files that are then combined at the end. 
- [Tool Paper Link for Reference](https://doi.org/10.1186/s13059-016-0974-4)
- [Tool Documentation Link for Reference](https://useast.ensembl.org/info/docs/tools/vep/index.html#publication)
- [Example Config File](https://github.com/PMBB-Informatics-and-Genomics/pmbb-geno-pheno-toolkit/tree/main/Example_Configs/vep_params.conf)
- [Example Parameters File](https://github.com/PMBB-Informatics-and-Genomics/pmbb-geno-pheno-toolkit/tree/main/Example_Configs/vep_plugins.yaml)
- [Example nextflow.config File](https://github.com/PMBB-Informatics-and-Genomics/pmbb-geno-pheno-toolkit/tree/main/Example_Configs/nextflow.config)

## Software Requirements


* [Nextflow version 24.04.3](https://www.nextflow.io/docs/latest/cli.html)

* [Singularity 3.8.3](https://sylabs.io/docs/) OR [Docker 4.30.0](https://docs.docker.com/)
## Commands for Running the Workflow


* Singularity Command: `singularity build vep.sif docker://ensemblorg/ensembl-vep:release_113.0`

* Docker Command: `docker pull ensemblorg/ensembl-vep:release_113.0`

* Pull from Google Container Registry: `docker pull gcr.io/verma-pmbb-codeworks-psom-bf87/vep:latest`

* Run Command: `nextflow run /path/to/toolkit/module/main.nf`

* Common `nextflow run` flags:

    * `-resume` flag picks up workflow where it left off

    * `-stub` performs a dry run, checks channels without executing code

    * `-profile` selects the compute profiles in nextflow.config

    * `-profile standard` uses the Docker image to execute processes

    * `-profile cluster` uses the Singularity container and submits processes to a queue

    * `-profile all_of_us` uses the Docker image on All of Us Workbench

* More info: [Nextflow documentation](https://www.nextflow.io/docs/latest/cli.html)
# Detailed Pipeline Steps

## Part I: Setup


1. Start your own tools directory and go there. You may do this in your project analysis directory, but it often makes sense to clone into a general `tools` location

```sh
# Make a directory to clone the pipeline into
TOOLS_DIR="/path/to/tools/directory"
mkdir $TOOLS_DIR
cd $TOOLS_DIR
```

2. Download the source code by cloning from git

```sh
git clone None
cd $TOOLS_DIR/pmbb-nf-toolkit-vep
```

3. Build the singularity image
    - you may call the image whatever you like, and store it wherever you like. Just make sure you specify the name in `nextflow.conf`
    - this does NOT have to be done for every saige-based analysis, but it is good practice to re-build every so often as we update regularly.


```sh
cd $TOOLS_DIR/pmbb-nf-toolkit-vep
singularity build vep.sif docker://ensemblorg/ensembl-vep:release_113.0
```
## Part II: Configure your run


1. Make a separate analysis/run/working directory.
    - The quickest way to get started, is to run the analysis in the folder the pipeline is run. However, subsequent analyses will over-write results from previous analyses.
    - ❗This step is optional, but We Highly recommend making a `tools` directory separate from your `run` directory. We recommend storing the `nextflow.conf` in here as it shouldn't change between runs.


```sh
WDIR="/path/to/analysis/run1"
mkdir -p $WDIR
cd $WDIR
```

2. Fill out the `nextflow.config` file for your system.
    - See [Nextflow configuration documentation](https://www.nextflow.io/docs/latest/config.html) for information on how to configure this file. An example can be found on our GitHub: [Nextflow Config](https://github.com/PMBB-Informatics-and-Genomics/pmbb-geno-pheno-toolkit/blob/main/Example_Configs/nextflow.config).
    - ❗IMPORTANTLY, you must configure a user-defined profile for your run environments (local, docker, saige, cluster, etc.). If multiple profiles are specified, run with a specific profile using `nextflow run -profile $MY_PROFILE`.
    - For singularity, The profile's attribute `process.container` should be set to `'/path/to/vep.sif'` (replace `/path/to` with the location where you built the image above). See [Nextflow Executor Information](https://www.nextflow.io/docs/latest/executor.html) for more details.
    - ⚠️As this file remains mostly unchanged for your system, We recommend storing this file in the `tools/pipeline` directory and passing it to the pipeline with `-c /path/to/nextflow.config`.


3. Create a pipeline-specific `.config` file specifying your run parameters and input files. See Below for workflow-specific parameters and what they mean.
    - Everything in here can be configured in `nextflow.config`, however we find it easier to separate the system-level profiles from the individual run parameters.
    - Examples can be found in our Pipeline-Specific [Example Config Files](https://github.com/PMBB-Informatics-and-Genomics/pmbb-geno-pheno-toolkit/tree/main/Example_Configs).
    - you can compartamentalize your config file as much as you like by passing
    - There are 2 ways to specify the config file during a run:

        - with the `-c` option on the command line: `nextflow run -c vep_params.conf`
        - in the `nextflow.config`: at the top of the file add: `includeConfig vep_params.conf`

## Part III: Run your analysis


❗We HIGHLY recommend doing a STUB run to test the analysis using the `-stub` flag. This is a dry run to make sure your environment, parameters, and input_files are specified and formatted correctly.❗We also HIGHLY recommend doing a TEST run with the included test data in `$TOOLS_DIR/pmbb-nf-toolkit-vep/test_data`we have several pre-configured analyses runs with input data and fully-specified config files.

```sh
# run an exwas stub
nextflow run $TOOLS_DIR/pmbb-nf-toolkit-vep/main.nf \
   -profile cluster \
   -c /path/to/nextflow.config \
   -c vep_params.conf \
   -stub

# run an exwas for real
nextflow run $TOOLS_DIR/pmbb-nf-toolkit-vep/main.nf \
   -profile cluster \
   -c /path/to/nextflow.config \
   -c vep_params.conf

# resume an exwas run if it was interrupted or ran into an error
nextflow run $TOOLS_DIR/pmbb-nf-toolkit-vep/main.nf \
   -profile cluster \
   -c /path/to/nextflow.config \
   -c vep_params.conf \
   -resume
```
# Pipeline Parameters

## Input Files for VEP


* batches_file

    * `batches_file` (Type: File Path)

    * tab-separated file mapping chunks to “batches” (i.e., chromosomes, but can be any grouping). The first column contains the batches and the second are the chunks defined in `chunks_file`. All chunks assigned to the same batch will be combined. This is useful when your chromosome files are broken up and you want to combine the chunks back into chromosomes (batches). If no merging of results are desired, there will be a 1:1 ratio for all chunks and the 2 columns will be identical for all rows. 

    * Type: Data Table

    * Format: tsv

    * File Header:


    ```
    1	1
    2	2
    3and4	3
    3and4	4
    5and6	5
    5and6	6
    7and8	7
    7and8	8
    9and10	9
    9and10	10
    11to15	11
    11to15	12
    11to15	13
    11to15	14
    11to15	15
    ```

* chunks_file

    * `chunks_file` (Type: File Path)

    * new-line separated list of chunk names to parallelize by. This can be chromosome numbers or `chromosome_chunk` names. Must be unique. The chunks should be in the input file names and  represent everything in between `input_prefix` and `input_suffix`

    * Type: List File

    * Format: txt

    * File Header:


    ```
    1
    2
    5
    22
    X
    Y
    ```

* vep_plugins.yaml

    * `plugins_config_file` (Type: File Path)

    * yaml-formatted file containing everything needed to each plugin. All paths are local, but prefixed with `"${vep_data_directory}”` which maps to `vep_data_directory/` directory defined in `vep_params.yaml`. 

The top level contains path to `ref_fasta` and anything else you might need. 

For each plugin, define 
  • `name` - your unique name for the plugin
  • `enabled` - `true` or `false` to enable or disable running that plugin
  • `variables` - any variables that need to be defined and put in the command.  paths can be absolute or use ${vep_data_directory} prefix
  • `command` - the command needed to run the plugin. This should contain the `--plugin` flag and everything else needed. Enclose variables with braces and a dollar sign for example: `${VARIABLE_NAME}` . 


  • Can also set group_file defaults

    * Type: config

    * Format: yaml

    * File Header:


    ```
    ref_fasta: "${vep_data_directory}/fastas/Homo_sapiens_assembly38_nochr.fasta”
    
    plugins:
    
      alphamissense:
        enabled: false
        command: "--plugin AlphaMissense,file=${AM_PATH}”
        variables: 
          AM_PATH: "${vep_data_directory}/alpha_missense/AlphaMissense_hg38.tsv.gz”
    
      everything:
        enabled: true
        command: “—everything”
    ```
## Output Files for VEP


* results_byChunk_byPlugin

    * `output_directory/results_byChunk_byPlugin`

    * path to directory containing tab-separated vep results files for each chunk-plugin combination. These are the precursor files before being combined into chunk-level results. 

    * Type: Data Table

    * Format: tsv

    * File Header:


    ```
    #Uploaded_variation     Location        Allele  Gene    Feature Feature_type    Consequence     cDNA_position   CDS_position    Protein_position
    chr22_15690143_C_G      chr22:15690143  G       ENSG00000198062 ENST00000343518 Transcript      missense_variant        118     66      22
    chr22_15690143_C_G      chr22:15690143  G       ENSG00000198062 ENST00000452800 Transcript      upstream_gene_variant   -       -       -
    chr22_15819981_C_A      chr22:15819981  A       ENSG00000206195 ENST00000383038 Transcript      downstream_gene_variant -       -       -
    chr22_15819981_C_A      chr22:15819981  A       ENSG00000206195 ENST00000413768 Transcript      intron_variant,non_coding_transcript_variant    -       -       -
    ```

        * Parallel By: Chunk, Plugin

* results_byChunk

    * `output_directory/results_byChunk`

    * path to directory containing tab-separated vep results files for each chunk. If more than one plugin was run, they will all be deduplicated, sorted, and concatenated by each chunk. 

    * Type: Data Table

    * Format: tsv

    * File Header:


    ```
    #Uploaded_variation     Location        Allele  Gene    Feature Feature_type    Consequence     cDNA_position   CDS_position    Protein_position
    chr22_15690143_C_G      chr22:15690143  G       ENSG00000198062 ENST00000343518 Transcript      missense_variant        118     66      22
    chr22_15690143_C_G      chr22:15690143  G       ENSG00000198062 ENST00000452800 Transcript      upstream_gene_variant   -       -       -
    chr22_15819981_C_A      chr22:15819981  A       ENSG00000206195 ENST00000383038 Transcript      downstream_gene_variant -       -       -
    chr22_15819981_C_A      chr22:15819981  A       ENSG00000206195 ENST00000413768 Transcript      intron_variant,non_coding_transcript_variant    -       -       -
    ```

        * Parallel By: Chunk
## Other Parameters for VEP

### Workflow


* `make_group_files` (Type: Bool (Java: true or false))

    * set `true` to generate BRaVa annotations and SAIGE formatted group files. Thresholds can be configured in `vep_plugins.yaml`. Requires the following columns/plugins enabled:
• `Uploaded_variation` (core VEP output, always present)
• `Gene` (core VEP output, always present)
• `gnomADe_AF` (gnomad) plugin
• `CADD_PHRED` (cadd) plugin
• `CADD_RAW` (cadd) plugin
• `LoF` (loftee) plugin
• `REVEL_score` (dbnsfp) plugin — pulled from dbNSFP's bundled `DBNSFP_FEATURES`, not a standalone REVEL plugin
• `SpliceAI_pred` (spliceai) plugin
• `Consequence` (everything) plugin
• `MANE_SELECT` (everything) plugin
• `CANONICAL` (everything) plugin
• `BIOTYPE` (everything) plugin
• `SYMBOL` (everything) plugin

* `python` (Type: File Path)

    * Optional Path to python. It is not included in docker/singularity container so it will use system default, which might not have pandas. 

* `download_vep_cache` (Type: Bool (Java: true or false))

    * Whether to download the vep_cache (fasta and cache) before starting the run. It is automatically configured to download `GRCh38` assembly of `homo_sapiens`. If you want to download your own data, follow instructions on the website and make sure to define a path to the downloaded data in `vep_params.conf`. 

* `batches_file` (Type: File Path)

    * Tab-separated table of batches:chunks. The first column are unique batch names without spaces (for example chromosome IDs). They can be anything — it doesn’t have to match filenames or chunk lists. The second column are all the chunks from `chunks_file` that belong to each batch. At the end of the run, any chunks that belong to the same batch will be merged and prefixed with the batch name. This can be used to combine chunks of chromosomes into full chromosomes or chromosomes into one monolithic results file. If no batching is needed, make batches:chunks 1:1. Can not be turned off at the moment. 

    * Corresponding Input File: batches_file

        * tab-separated file mapping chunks to “batches” (i.e., chromosomes, but can be any grouping). The first column contains the batches and the second are the chunks defined in `chunks_file`. All chunks assigned to the same batch will be combined. This is useful when your chromosome files are broken up and you want to combine the chunks back into chromosomes (batches). If no merging of results are desired, there will be a 1:1 ratio for all chunks and the 2 columns will be identical for all rows. 

        * Type: Data Table

        * Format: tsv

        * File Header:


        ```
        1	1
        2	2
        3and4	3
        3and4	4
        5and6	5
        5and6	6
        7and8	7
        7and8	8
        9and10	9
        9and10	10
        11to15	11
        11to15	12
        11to15	13
        11to15	14
        11to15	15
        ```

* `output_directory` (Type: File Path)

    * Optional Path to desired output directory. Default = `${launchDir}`. Define in `vep_params.conf`.

* `chunks_file` (Type: File Path)

    * newline-separated List of chunk names to run. The chunk should be everything between `input_prefix` and `input_suffix.` The filename should have the following syntax: `${input_prefix}${chunk_name}${input_suffix}` - no periods will be added between the parts. 

    * Corresponding Input File: chunks_file

        * new-line separated list of chunk names to parallelize by. This can be chromosome numbers or `chromosome_chunk` names. Must be unique. The chunks should be in the input file names and  represent everything in between `input_prefix` and `input_suffix`

        * Type: List File

        * Format: txt

        * File Header:


        ```
        1
        2
        5
        22
        X
        Y
        ```

* `cpu` (Type: Integer)

    * Number of CPUs to use per process. Default = 1. Define in `vep_params.conf`.

* `input_suffix` (Type: String)

    * Suffix for the input files - everything that comes after the chunk name derived from `chunks_file` . Define in `vep_params.conf` . NOTE: Should include leading period, for example (`.vcf.gz`)

* `input_prefix` (Type: String)

    * Prefix to input filenames that come before chunk name derived from `chunks_file`. If no prefix, set to empty string `""` . Define in `vep_params.conf`

* `input_directory` (Type: File Path)

    * Path to input files. Define in `vep_params.conf`

* `vep_sif` (Type: File Path)

    * Path to vep singularity image. Define in `vep_params.conf`.

* `vep_data_directory` (Type: File Path)

    * Path to directory containing local VEP annotation databases. This path can be referenced in `vep_plugins.yaml` as `${vep_data_directory}` Define in `vep_params.conf`

* `plugins_config_file` (Type: File Path)

    * Path to plugins configuration YAML file. Define in `vep_params.conf`

    * Corresponding Input File: vep_plugins.yaml

        * yaml-formatted file containing everything needed to each plugin. All paths are local, but prefixed with `"${vep_data_directory}”` which maps to `vep_data_directory/` directory defined in `vep_params.yaml`. 

The top level contains path to `ref_fasta` and anything else you might need. 

For each plugin, define 
  • `name` - your unique name for the plugin
  • `enabled` - `true` or `false` to enable or disable running that plugin
  • `variables` - any variables that need to be defined and put in the command.  paths can be absolute or use ${vep_data_directory} prefix
  • `command` - the command needed to run the plugin. This should contain the `--plugin` flag and everything else needed. Enclose variables with braces and a dollar sign for example: `${VARIABLE_NAME}` . 


  • Can also set group_file defaults

        * Type: config

        * Format: yaml

        * File Header:


        ```
        ref_fasta: "${vep_data_directory}/fastas/Homo_sapiens_assembly38_nochr.fasta”
        
        plugins:
        
          alphamissense:
            enabled: false
            command: "--plugin AlphaMissense,file=${AM_PATH}”
            variables: 
              AM_PATH: "${vep_data_directory}/alpha_missense/AlphaMissense_hg38.tsv.gz”
        
          everything:
            enabled: true
            command: “—everything”
        ```
# Configuration and Advanced Workflow Files
