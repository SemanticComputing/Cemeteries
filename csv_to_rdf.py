#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Convert cemeteries from CSV to RDF.
"""

import argparse
# import datetime
import logging
# import re

import pandas as pd
from rdflib import URIRef, Graph, Literal
from mapping import CEMETERY_MAPPING
from namespaces import *


class RDFMapper:
    """
    Map tabular data (currently pandas DataFrame) to RDF. Create a class instance of each row.
    """

    def __init__(self, mapping, instance_class, loglevel='WARNING'):
        self.mapping = mapping
        self.instance_class = instance_class
        self.table = None
        self.data = Graph()
        self.schema = Graph()
        logging.basicConfig(filename='cemeteries.log',
                            filemode='a',
                            level=getattr(logging, loglevel),
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        self.log = logging.getLogger(__name__)

    def map_row_to_rdf(self, entity_uri, row):
        """
        Map a single row to RDF.

        :param entity_uri: URI of the instance being created
        :param row: tabular data
        :return:
        """

        row_rdf = Graph()

        # Loop through the mapping dict and convert data to RDF
        for column_name in self.mapping:

            mapping = self.mapping[column_name]

            value = row[column_name]

            converter = mapping.get('converter')
            value = converter(value) if converter else value

            if value:
                if column_name == 'pituus_n' or column_name == 'leveys_e':
                    liter = Literal(value, datatype=XSD.float)
                else:
                    liter = Literal(value)
                # liter = Literal(value, datatype=XSD.date) if type(value) == datetime.date else Literal(value)
                row_rdf.add((entity_uri, mapping['uri'], liter))

            if row_rdf:
                row_rdf.add((entity_uri, RDF.type, self.instance_class))
            else:
                # Don't create class instance if there is no data about it
                logging.debug('No data found for {uri}'.format(uri=entity_uri))

        return row_rdf

    def read_csv(self, csv_input):
        """
        Read in a CSV files using pandas.read_csv

        :param csv_input: CSV input (filename or buffer)
        """
        csv_data = pd.read_csv(csv_input, encoding='UTF-8', index_col=False, sep=';', quotechar='"',
                               # parse_dates=[1], infer_datetime_format=True, dayfirst=True,
                               na_values=[' '], converters={'ammatti': lambda x: x.lower()})

        self.table = csv_data.fillna('').applymap(lambda x: x.strip() if type(x) == str else x)
        self.log.info('Data read from CSV %s' % csv_input)

    def serialize(self, destination_data, destination_schema):
        """
        Serialize RDF graphs

        :param destination_data: serialization destination for data
        :param destination_schema: serialization destination for schema
        :return: output from rdflib.Graph.serialize
        """
        self.data.bind("c", "http://ldf.fi/warsa/temp/")
        self.data.bind("cs", "http://ldf.fi/schema/warsa/cemeteries/")
        self.data.bind("skos", "http://www.w3.org/2004/02/skos/core#")
        self.data.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.data.bind("foaf", 'http://xmlns.com/foaf/0.1/')
        self.data.bind("bioc", 'http://ldf.fi/schema/bioc/')

        self.schema.bind("cs", "http://ldf.fi/schema/warsa/cemeteries/")
        self.schema.bind("skos", "http://www.w3.org/2004/02/skos/core#")
        self.schema.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.schema.bind("foaf", 'http://xmlns.com/foaf/0.1/')
        self.schema.bind("bioc", 'http://ldf.fi/schema/bioc/')

        data = self.data.serialize(format="turtle", destination=destination_data)
        schema = self.schema.serialize(format="turtle", destination=destination_schema)
        self.log.info('Data serialized to %s' % destination_data)
        self.log.info('Schema serialized to %s' % destination_schema)

        return data, schema  # Return for testing purposes

    def process_rows(self):
        """
        Loop through CSV rows and convert them to RDF
        """
        # column_headers = list(self.table)
        #
        for index in range(len(self.table)):
            cemetery_uri = DATA_NS['cemetery_' + str(index)]
            row_rdf = self.map_row_to_rdf(cemetery_uri, self.table.ix[index])
            if row_rdf:
                self.data += row_rdf

        for prop in CEMETERY_MAPPING.values():
            self.schema.add((prop['uri'], RDF.type, RDF.Property))
            if 'name_fi' in prop:
                self.schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_fi'], lang='fi')))
            if 'name_en' in prop:
                self.schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_en'], lang='en')))


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(description="Process cemeteries CSV", fromfile_prefix_chars='@')

    argparser.add_argument("input", help="Input CSV file")
    argparser.add_argument("output", help="Output location to serialize RDF files to")
    argparser.add_argument("mode", help="CSV conversion mode", default="CEMETERIES", choices=["CEMETERIES"])
    argparser.add_argument("--loglevel", default='INFO', help="Logging level, default is INFO.",
                           choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

    args = argparser.parse_args()

    output_dir = args.output + '/' if args.output[-1] != '/' else args.output

    if args.mode == "CEMETERIES":
        mapper = RDFMapper(CEMETERY_MAPPING, SCHEMA_NS.TempCemetery, loglevel=args.loglevel.upper())
        mapper.read_csv(args.input)

        mapper.process_rows()

        mapper.serialize(output_dir + "cemeteries.ttl", output_dir + "schema.ttl")

    

