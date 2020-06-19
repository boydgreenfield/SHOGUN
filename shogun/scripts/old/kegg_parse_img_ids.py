#!/usr/bin/env python
"""
Copyright 2015-2020 Knights Lab, Regents of the University of Minnesota.

This software is released under the GNU Affero General Public License (AGPL) v3.0 License.
"""

from __future__ import print_function, division

import argparse
import sys
from collections import defaultdict
import os
import csv

from shogun import SETTINGS

from dojo.taxonomy.maps import IMGMap
from dojo.taxonomy import NCBITree


def make_arg_parser():
    parser = argparse.ArgumentParser(description='Get least common ancestor for alignments in unsorted BAM/SAM file')
    parser.add_argument('-i', '--input', help='The folder containing the SAM files to process.', required=True, type=str)
    parser.add_argument('-o', '--output', help='If nothing is given, then STDOUT, else write to file')
    parser.add_argument('-t', '--threads', help='The number of threads to use.', default=SETTINGS.N_jobs, type=int)
    parser.add_argument('-d', '--depth', help='The depth of the search (7=species default)', default=7, type=int)
    parser.add_argument('-v', '--verbose', help='Print extra statistics', action='store_true', default=False)
    return parser


def yield_alignments_from_sam_inf(inf):
    csv_inf = csv.reader(inf, delimiter='\t'
                         )
    for line in csv_inf:
        # this function yields qname, rname
        rname = line[2].split('|')[-1]
        yield line[0], rname


def build_lca_map(align_gen, tree, img_map):
    """
    Expects the reference names to be annotated like ncbi_tid|<ncbi_tid>|<img_oid.img_gid>
    :param align_gen:
    :param tree:
    :param img_map:
    :return:
    """
    lca_map = defaultdict(lambda: [set(), None])
    for qname, rname in align_gen:
        img_id = int(rname.split('|')[-1].split('_')[0])
        if qname in lca_map:
            ncbi_tid_string = rname.split('|')[1]
            if ncbi_tid_string != 'NA':
                ncbi_tid_current = lca_map[qname][1]
                ncbi_tid_new = int(ncbi_tid_string)
                if ncbi_tid_new and ncbi_tid_current:
                    if ncbi_tid_current != ncbi_tid_new:
                        lca_map[qname][1] = tree.lowest_common_ancestor(ncbi_tid_current, ncbi_tid_new)
        else:
            lca_map[qname][1] = img_map(img_id)
        lca_map[qname][0].add(img_id)
    return lca_map


def main():
    parser = make_arg_parser()
    args = parser.parse_args()

    sam_files = [os.path.join(args.input, filename) for filename in os.listdir(args.input) if filename.endswith('.sam')]

    img_map = IMGMap()

    ncbi_tree = NCBITree()

    with open(args.output, 'w') if args.output else sys.stdout as outf:
        csv_outf = csv.writer(outf, quoting=csv.QUOTE_ALL, lineterminator='\n')
        csv_outf.writerow(['sample_id', 'sequence_id', 'ncbi_tid', 'img_id'])
        for file in sam_files:
            with open(file) as inf:
                lca_map = build_lca_map(yield_alignments_from_sam_inf(inf), ncbi_tree, img_map)
                for key in lca_map:
                    img_ids, ncbi_tid = lca_map[key]
                    csv_outf.writerow([os.path.basename(file)[:-4],  key, ncbi_tid, ','.join(img_ids)])

if __name__ == '__main__':
    main()
