#!/usr/bin/env python3
import argparse
import os.path
import pandas as pd
import requests

import encodedcc

"""

Purpose
-------
Find orphaned ENCODE objects.

Example
-------
A Biosample with no Libraries means that a Biosample
was created and then never referred to by a Library.
The Biosample is orphaned.

Method
-------
This script gathers all accession/uuids of child objects
and all accession/uuids of child objects embedded in parent
objects and reports the difference.

"""

# Define parent-child relationship:
# A child is the possible orphan while a parent is any
# object that could refer to it (as defined in the schema
# at https://www.encodeproject.org/profiles/). The child
# can have one parent or multiple parents (e.g. Documents).
# To define an orphan, add a new object to the 'orphans' list,
# where 'child' is the possible orphan object, 'child_field'
# is its identification field (accession/uuid/@id), 'parent'
# is the parent object (or list of parent objects), and 'parent_field'
# is the child's identification field (accession/uuid/@id) in
# the parent (a list is required if there are multiple parents,
# and the 'parent' list and 'parent_field' list must be same length.
orphans = [{'child': 'Biosample',
            'child_field': 'accession',
            'parent': 'Library',
            'parent_field': 'biosample.accession'},
           {'child': 'Donor',
            'child_field': 'accession',
            'parent': 'Biosample',
            'parent_field': 'donor.accession'},
           {'child': 'Library',
            'child_field': 'accession',
            'parent': 'Replicate',
            'parent_field': 'library.accession'},
           {'child': 'AnalysisStep',
            'child_field': 'uuid',
            'parent': 'Pipeline',
            'parent_field': 'analysis_steps.uuid'},
           {'child': 'Construct',
            'child_field': '@id',
            'parent': ['Biosample',
                       'ConstructCharacterization'],
            'parent_field': ['constructs.@id',
                             'constructs.@id']
            },
           {'child': 'Document',
            'child_field': '@id',
            'parent':  ['AnalysisStep',
                        'Annotation',
                        'AntibodyCharacterization',
                        'Biosample',
                        'BiosampleCharacterization',
                        'Characterization',
                        'Construct',
                        'ConstructCharacterization',
                        'Crispr',
                        'Dataset',
                        'Donor',
                        'DonorCharacterization',
                        'Experiment',
                        'FileSet',
                        'FlyDonor',
                        'GeneticModification',
                        'GeneticModificationCharacterization',
                        'HumanDonor',
                        'Library',
                        'MatchedSet',
                        'ModificationTechnique',
                        'MouseDonor',
                        'OrganismDevelopmentSeries',
                        'Pipeline',
                        'Project',
                        'PublicationData',
                        'Reference',
                        'ReferenceEpigenome',
                        'ReplicationTimingSeries',
                        'RNAi',
                        'Series',
                        'Treatment',
                        'TreatmentConcentrationSeries',
                        'TreatmentTimeSeries',
                        'UcscBrowserComposite',
                        'WormDonor',
                        'File'],
            'parent_field': ['documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'documents.@id',
                             'file_format_specification.@id']}]


def get_accessions(item_type, field_name):
    """Return set of accessions/uuids/@ids given
    the ENCODE item type and field name defining
    location of accessions/uuids/@ids.
    """
    accessions = []
    childless_parents = []
    field_name_split = field_name.split('.')
    # Grab all objects of that type.
    url = 'https://www.encodeproject.org/search/'\
          '?type={}&limit=all&format=json'\
          '&frame=embedded'.format(item_type)
    r = requests.get(url, auth=(key.authid, key.authpw))
    results = r.json()['@graph']
    print('Total {}: {}'.format(item_type, len(results)))
    # Process each object one at a time.
    for result in results:
        value, values = result, None
        # Access value in nested fields if required.
        for name in field_name_split:
            # Deal with list of objects.
            if isinstance(value, list):
                # Recover all values in a list.
                values = [x.get(name) if isinstance(x, dict)
                          else x for x in value]
                # Set singluar value to None because
                # now have multiple values.
                value = None
                # Recovered values so exit loop.
                break
            # Otherwise access field name and update value.
            value = value.get(name, {})
        # Deal with objects missing field. An empty dict
        # is returned if field not present.
        if isinstance(value, dict):
            childless_parents.append(result.get('accession',
                                                result.get('uuid')))
            continue
        # See if replacement is also orphaned (only for child objects).
        if ((result.get('status') == 'replaced')
                and (len(field_name_split) == 1)):
            url = 'https://www.encodeproject.org/'\
                  '{}/?format=json'.format(result.get('accession',
                                                      result.get('uuid',
                                                                 result.get('@id'))))
            r = requests.get(url, auth=(key.authid, key.authpw))
            if (r.status_code == 200):
                r = r.json()
                # Set replaced accession to replacement accession.
                value = r.get('accession',
                              r.get('uuid',
                                    r.get('@id')))
        # Deal with values recovered from a list of objects/strings.
        if values is not None:
            # Possible to have empty list.
            if len(values) == 0:
                childless_parents.append(result.get('accession',
                                                    result.get('uuid')))
            else:
                # Add recovered values to accessions list.
                accessions.extend(values)
            continue
        # Add recovered value to accessions list.
        accessions.append(value)
    if childless_parents:
        print('Number of {} missing {} field'
              ' (childless parents): {}'.format(item_type,
                                                field_name,
                                                len(childless_parents)))
    return set(accessions)


def find_orphans(i, item):
    """Return orphans of specified child item"""
    orphan_data = []
    # Grab all relationships in 'orphans' list with specified child.
    relationships = [x for x in orphans if x['child'].lower() == item]
    for relation in relationships:
        child, parent, child_field, parent_field = (relation['child'],
                                                    relation['parent'],
                                                    relation['child_field'],
                                                    relation['parent_field'])
        print('{}. {} not associated with {}'.format((i + 1), child, parent))
        # Grab set of child accessions.
        child_accessions = get_accessions(child, child_field)
        # Grab set of parent accessions.
        # Deal with multiple parents.
        if isinstance(parent, list):
            # Build set from multiple parents.
            parent_accessions = set()
            for p, f in zip(parent, parent_field):
                accessions = get_accessions(p, f)
                parent_accessions = parent_accessions.union(accessions)
        else:
            # If only single parent.
            parent_accessions = get_accessions(parent, parent_field)
        # Compare groups.
        same = child_accessions.intersection(parent_accessions)
        different = child_accessions.difference(parent_accessions)

        print('Number of {} with {} (families): {}'.format(child,
                                                           parent,
                                                           len(same)))
        print('Number of {} without {} (orphans): {}'.format(child,
                                                             parent,
                                                             len(different)))
        orphan_data.append((child, parent, different))
    return orphan_data


def get_args():
    parser = argparse.ArgumentParser(description='__doc__')
    parser.add_argument('--type',
                        default=None,
                        help='Specify item type (or list of comma-separated'
                        ' item types in quotation marks) to check for orphans.'
                        ' Default is None.')
    parser.add_argument('--keyfile',
                        default=os.path.expanduser('~/keypairs.json'),
                        help='The keypair file. Default is {}.'
                        .format(os.path.expanduser('~/keypairs.json')))
    parser.add_argument('--key',
                        default='default',
                        help='The keypair identifier from the keyfile.'
                        ' Default is --key=default.')
    return parser.parse_args()


def main():
    global key
    global args
    args = get_args()
    key = encodedcc.ENC_Key(args.keyfile, args.key)
    # Build list of ENCODE object types for orphan checking.
    if args.type is None:
        # Default list.
        item_type = [x['child'].lower() for x in orphans]
        print('Default orphan search:')
    else:
        # User-defined list.
        input_type = [x.strip().lower() for x in args.type.split(',')]
        item_type = [x for x in input_type
                     if x in [x['child'].lower() for x in orphans]]
        # Check for invalid --type input from user.
        if len(input_type) != len(item_type):
            raise ValueError("Invalid item type: {}.".format((set(input_type)
                                                              - set(item_type))))
        print('Custom orphan search:')
    return [find_orphans(i, item) for i, item in enumerate(item_type)]


if __name__ == '__main__':
    results = main()
