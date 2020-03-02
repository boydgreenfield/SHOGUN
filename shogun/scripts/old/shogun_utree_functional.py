#!/usr/bin/env python
"""
Copyright 2015-2020 Knights Lab, Regents of the University of Minnesota.

This software is released under the GNU Affero General Public License (AGPL) v3.0 License.

function repertiore prediction with utree species/strain classification
"""

import click
import os
import csv
import numpy as np

from dojo.taxonomy import NCBITree

from ninja_utils.utils import verify_make_dir

from shogun.wrappers import utree_search


@click.command()
@click.option('-i', '--input', type=click.Path(), default=os.getcwd(), help='directory containing the input fasta files with ".fna" extensions (default=cwd)')
@click.option('-o', '--output', type=click.Path(), default=os.path.join(os.getcwd(), 'shogun_utree_lca_out'), help='output directory for the results')
@click.option('-u', '--utree_indx', required=True, help='path to the bowtie2 index')
@click.option('-p', '--threads', type=click.INT, default=1, help='the number of threads to use (default=1)')
def shogun_utree_functional(input, output, utree_indx, threads):
    verify_make_dir(output)

    basenames = [os.path.basename(filename)[:-4] for filename in os.listdir(input) if filename.endswith('.fna')]

    # Run the species pipeline
    # TODO make this a reusable function
    for basename in basenames:
        fna_file = os.path.join(input, basename + '.fna')
        tsv_outf = os.path.join(output, basename + '.species.utree.tsv')
        if not os.path.isfile(tsv_outf):
            print(utree_search(utree_indx, fna_file, tsv_outf))
        else:
            print("found the output file \"%s\". skipping the species alignment phase for this file." % tsv_outf)

    # Run the strain pipeline
    for basename in basenames:
        fna_file = os.path.join(input, basename + '.fna')
        tsv_outf = os.path.join(output, basename + '.strain.utree.tsv')
        if not os.path.isfile(tsv_outf):
            print(utree_search(utree_indx, fna_file, tsv_outf))
        else:
            print("found the output file \"%s\". skipping the strain alignment phase for this file." % tsv_outf)

    # Track the hit rates
    basename_counts = np.zeros(len(basenames))
    # Track the hit rates
    basename_counts_hits = np.zeros(len(basenames))
    basename_counts_hits_strain = np.zeros(len(basenames))

    # Run the species strain pipeline
    for basename_ix, basename in enumerate(basenames):
        species_tsv = os.path.join(output, basename + '.species.utree.tsv')
        strain_tsv = os.path.join(output, basename + '.strain.utree.tsv')
        # Keep track of the number of times that species and strain are not equivalent
        discordance_count = 0
        # Lists for redistribute information
        species_lca = []
        strain_lca = []
        # Track the confidence for each LCA
        species_conf = []
        strain_conf = []
        with open(species_tsv) as species_inf:
            species_reader = csv.reader(species_inf, delimiter="\t")
            with open(strain_tsv) as strain_inf:
                strain_reader = csv.reader(strain_inf, delimiter="\t")
                for species, strain in zip(species_reader, strain_reader):
                    # Track the number of reads
                    basename_counts[basename_ix] += 1
                    # Check if alignment was made in species
                    if species[1]:
                        # Now we check for strain redistribute
                        species_tax = species[1].split('; ')
                        if strain[1]:
                            strain_tax = strain[1].split('; ')
                            basename_counts_hits[basename_ix] += 1
                            # Check for equivalence of strain and species query names
                            assert(strain[0] == species[0])
                            # If they match
                            if strain_tax[-2] == species_tax[-1]:
                                # TODO: Check for strain confidence here
                                strain_conf.append(float(strain[2]))
                                strain_lca.append('; '.join(species_tax))
                                basename_counts_hits_strain[basename_ix] += 1
                            # If they don't match
                            else:
                                discordance_count += 1
                        # TODO: Check for species confidence here
                        species_conf.append(float(species[2]))
                        species_lca.append('; '.join(species_tax)


        # Verify strain confidence is below species confidence
        mean_strain_conf = np.mean(strain_conf)
        mean_species_conf = np.mean(species_conf)
        print('strain conf\t%f.2\tspecies conf\t%f.2\t' % (mean_strain_conf, mean_species_conf))
        if mean_strain_conf <= mean_species_conf:
            print('Confidence checks out')
        else:
            print('CONFIDENCE IS BROKEN')

        # Print DISCORDANCE
        print(discordance_count)

        # Print number reads
        print("Number reads\t%d" % (basename_counts[basename_ix]))

        # Print ratio of assigned
        print("Percent hits species reads\t%f.2" % ((basename_counts_hits[basename_ix]/basename_counts[basename_ix])*100))

        # Print ratio of assigned
        print("Percent hits strain reads\t%f.2" % ((basename_counts_hits_strain[basename_ix]/basename_counts[basename_ix])*100))

if __name__ == '__main__':
    shogun_utree_functional()
