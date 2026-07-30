#!/usr/bin/env python3

import os
import math
import argparse
import gzip
import re

def parse_chromosome_regions(regions_file):
    """Parse the chromosome regions file and organize by chromosome."""
    chrom_regions = {}
    
    with open(regions_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                chrom, position = parts[0], int(parts[1])
                
                if chrom not in chrom_regions:
                    chrom_regions[chrom] = []
                
                chrom_regions[chrom].append(position)
    
    return chrom_regions

def create_chunk_files(chrom_regions, output_dir, num_chunks=5):
    """Create chunked region files for each chromosome."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Track created files for report
    created_files = []
    
    for chrom, positions in chrom_regions.items():
        # Sort positions
        positions.sort()
        
        # Calculate chunk size
        chunk_size = math.ceil(len(positions) / num_chunks)
        
        # Remove 'chr' prefix if present for file naming
        chrom_name = chrom.replace('chr', '')
        
        # Create chunks
        for i in range(num_chunks):
            chunk_num = i + 1
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(positions))
            
            if start_idx >= len(positions):
                break
                
            chunk_positions = positions[start_idx:end_idx]
            
            # Create output filename
            output_file = f"{output_dir}/chromosome_{chrom_name}_chunk{chunk_num:02d}.regions.txt"
            created_files.append(output_file)
            
            # Write positions to file
            with open(output_file, 'w') as f:
                for pos in chunk_positions:
                    f.write(f"{chrom}\t{pos}\n")
    
    return created_files

def generate_processing_script(input_dir, output_dir, created_files):
    """Generate a bash script to process the VCF files using the chunked regions."""
    script_path = f"{output_dir}/process_vcf_chunks.sh"
    
    with open(script_path, 'w') as f:
        f.write("#!/bin/bash\n\n")
        f.write("# Script to process VCF files in chunks\n\n")
        
        # Create output directory
        f.write(f"mkdir -p {output_dir}/chunked_vcfs\n\n")
        
        # Process each chunk file
        for chunk_file in created_files:
            # Extract chromosome and chunk number from filename
            match = re.search(r'chromosome_([^_]+)_chunk(\d+)', chunk_file)
            if match:
                chrom, chunk_num = match.groups()
                
                input_vcf = f"{input_dir}/chromosome_{chrom}.info.vcf.gz"
                output_vcf = f"{output_dir}/chunked_vcfs/chromosome_{chrom}_chunk{chunk_num}.info.vcf.gz"
                
                # Add command to extract regions from VCF
                # This is a placeholder - replace with your actual command
                f.write(f"# Process chromosome {chrom}, chunk {chunk_num}\n")
                f.write(f"bcftools view -R {chunk_file} {input_vcf} -Oz -o {output_vcf}\n\n")
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    return script_path

def main():
    parser = argparse.ArgumentParser(description='Split chromosome regions into chunks')
    parser.add_argument('regions_file', help='Input chromosome regions file')
    parser.add_argument('--vcf-dir', default='.', help='Directory containing VCF files')
    parser.add_argument('--output-dir', default='./chunked_regions', help='Output directory for chunked files')
    parser.add_argument('--num-chunks', type=int, default=5, help='Number of chunks per chromosome')
    
    args = parser.parse_args()
    
    # Parse regions file
    print(f"Parsing chromosome regions from {args.regions_file}...")
    chrom_regions = parse_chromosome_regions(args.regions_file)
    
    # Report chromosomes found
    print(f"Found {len(chrom_regions)} chromosomes: {', '.join(sorted(chrom_regions.keys()))}")
    for chrom, positions in chrom_regions.items():
        print(f"  {chrom}: {len(positions)} positions")
    
    # Create chunk files
    print(f"\nCreating {args.num_chunks} chunk files per chromosome in {args.output_dir}...")
    created_files = create_chunk_files(chrom_regions, args.output_dir, args.num_chunks)
    
    # Generate processing script
    print("\nGenerating processing script...")
    script_path = generate_processing_script(args.vcf_dir, args.output_dir, created_files)
    
    print(f"\nProcessing complete!")
    print(f"Created {len(created_files)} chunk files")
    print(f"Processing script generated at: {script_path}")
    print("\nUse the processing script to split your VCF files:")
    print(f"  $ bash {script_path}")

if __name__ == "__main__":
    main()