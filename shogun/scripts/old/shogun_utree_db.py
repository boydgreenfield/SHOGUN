#!/usr/bin/env python
"""
Copyright 2015-2020 Knights Lab, Regents of the University of Minnesota.

This software is released under the GNU Affero General Public License (AGPL) v3.0 License.
"""

import click
import os

from ninja_utils.utils import verify_make_dir
from ninja_utils.parsers import FASTA

from dojo.database import RefSeqDatabase
from dojo.taxonomy import NCBITree
from dojo.annotaters import GIAnnotater, RefSeqAnnotater, NTAnnotater, NCBIAnnotater

from shogun.wrappers import utree_build, utree_compress
from shogun import SETTINGS


@click.command()
@click.option('-i', '--input', type=click.Path(), help='The input FASTA file for annotating with NCBI TID')
@click.option('-o', '--output', type=click.Path(), default=os.path.join(os.getcwd(), 'annotated'),
              help='The directory to output the formatted DB and UTree db', show_default=True)
@click.option('-a', '-annotater', type=click.Choice(['gi', 'refseq', 'nt', 'ncbi']), default='refseq', help='The annotater to use.',
              show_default=True)
@click.option('-x', '--extract_id', default='ref|,|',
              help='Characters that sandwich the RefSeq Accession Version in the reference FASTA', show_default=True)
@click.option('-p', '--threads', type=click.INT, default=SETTINGS.N_jobs, help='The number of threads to use',
              show_default=True)
@click.option('--prefixes', default='*',
              show_default=True)
@click.option('-d', '--depth', default=7, help="The depth to annotate the map, max of 8 with strain.")
@click.option('-f', '--depth-force', default=True, help="Force the depth criterion if missing annotation",
              show_default=True)
def shogun_utree_db(input, output, annotater, extract_id, threads, prefixes, depth, depth_force):
    verify_make_dir(output)
    # Verify the FASTA is annotated
    if input == '-':
        output_fn = 'stdin'
    else:
        output_fn = '.'.join(str(os.path.basename(input)).split('.')[:-1])

    outf_fasta = os.path.join(output, output_fn + '.annotated.fna')
    outf_map = os.path.join(output, output_fn + '.annotated.map')
    if not os.path.isfile(outf_fasta) or not os.path.isfile(outf_map):
        tree = NCBITree()
        db = RefSeqDatabase()

        if annotater == 'refseq':
            annotater_class = RefSeqAnnotater(extract_id, prefixes, db, tree, depth=depth, depth_force=depth_force)
        elif annotater == 'nt':
            annotater_class = NTAnnotater(extract_id, prefixes, db, tree, depth=depth, depth_force=depth_force)
        elif annotater == 'ncbi':
            annotater_class = NCBIAnnotater(extract_id, tree, depth=depth, depth_force=depth_force)
        else:
            annotater_class = GIAnnotater(extract_id, db, tree, depth=depth, depth_force=depth_force)

        with open(outf_fasta, 'w') as output_fna:
            with open(outf_map, 'w') as output_map:
                with open(input) as inf:
                    inf_fasta = FASTA(inf)
                    for lines_fna, lines_map in annotater_class.annotate(inf_fasta.read()):
                        output_fna.write(lines_fna)
                        output_map.write(lines_map)
    else:
        print("Found the output files \"%s\" and \"%s\". Skipping the annotation phase for this file." % (
            outf_fasta, outf_map))

    # Build the output CTR
    verify_make_dir(os.path.join(output, 'utree'))
    path_uncompressed_tree = os.path.join(output, 'utree', output_fn + '.utr')
    path_compressed_tree = os.path.join(output, 'utree', output_fn + '.ctr')
    if os.path.exists(path_compressed_tree):
        print('Compressed tree database file %s exists, skipping this step.' % path_compressed_tree)
    else:
        if not os.path.exists(path_uncompressed_tree):
            print(utree_build(outf_fasta, outf_map, path_uncompressed_tree, threads=threads))
        print(utree_compress(path_uncompressed_tree, path_compressed_tree))
        os.remove(path_uncompressed_tree)


if __name__ == '__main__':
    shogun_utree_db()
