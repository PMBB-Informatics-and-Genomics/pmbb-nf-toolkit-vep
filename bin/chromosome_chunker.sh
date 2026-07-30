#!/bin/bash

# Usage: ./split_chromosomes.sh chromosome_regions.txt vcf_directory output_directory

# Check arguments
if [ $# -lt 3 ]; then
    echo "Usage: $0 chromosome_regions.txt vcf_directory output_directory number_chunks"
    exit 1
fi

REGIONS_FILE=$1
VCF_DIR=$2
OUTPUT_DIR=$3
NUM_CHUNKS=$4

# Create output directories
mkdir -p "$OUTPUT_DIR/regions"
mkdir -p "$OUTPUT_DIR/vcfs"

# Split regions file by chromosome
echo "Splitting regions file by chromosome..."
awk '{print > "'$OUTPUT_DIR'/regions/regions_"$1".txt"}' "$REGIONS_FILE"

# Process each chromosome file
for CHROM_FILE in "$OUTPUT_DIR"/regions/regions_chr*.txt; do
    # Extract chromosome number from filename
    CHROM=$(basename "$CHROM_FILE" | sed 's/regions_chr\(.*\)\.txt/\1/')
    
    echo "Processing chromosome $CHROM..."
    
    # Count lines in the chromosome file
    TOTAL_LINES=$(wc -l < "$CHROM_FILE")
    CHUNK_SIZE=$(( (TOTAL_LINES + NUM_CHUNKS - 1) / NUM_CHUNKS ))
    
    # Split chromosome file into chunks
    split -l "$CHUNK_SIZE" "$CHROM_FILE" "$OUTPUT_DIR/regions/chr${CHROM}_chunk_" --numeric-suffixes=1 --suffix-length=2
    
    # Process each chunk
    for CHUNK_FILE in "$OUTPUT_DIR"/regions/chr${CHROM}_chunk_*; do
        CHUNK_NUM=$(basename "$CHUNK_FILE" | sed 's/.*_\([0-9]*\)$/\1/')
        
        echo "  Processing chunk $CHUNK_NUM..."
        
        # Create output VCF filename
        OUTPUT_VCF="$OUTPUT_DIR/vcfs/chromosome_${CHROM}_chunk${CHUNK_NUM}.info.vcf.gz"
        
        # Find input VCF file
        INPUT_VCF="$VCF_DIR/chromosome_${CHROM}.info.vcf.gz"
        
        if [ -f "$INPUT_VCF" ]; then
            echo "    Extracting regions to $OUTPUT_VCF..."
            # Extract regions using bcftools
            bcftools view -R "$CHUNK_FILE" "$INPUT_VCF" -Oz -o "$OUTPUT_VCF"
        else
            echo "    Warning: Input VCF file $INPUT_VCF not found!"
        fi
    done
done

echo "Processing complete!"