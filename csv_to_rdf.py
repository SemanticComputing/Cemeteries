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
        self.photographs = Graph()
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

            liter = None
            current_municipality = None
            former_municipality = None
            narc_name = None

            if value and value != 'ei_ole':
                if column_name == 'pituus_n' or column_name == 'leveys_e':
                    liter = Literal(value, datatype=XSD.float)
                elif column_name == 'nykyiset_kunnat':
                    if isinstance(value, list):
                        current_municipality = Literal(value[0])
                        former_municipality = Literal(value[1].split(',')[0])
                        narc_name = Literal(value[1])
                    else:
                        current_municipality = Literal(value.split(',')[0])
                        former_municipality = None
                        narc_name = Literal(value)
                elif column_name == 'hautausmaan_nimi' and value == 'ei_ole':
                    alt_name = row['nykyiset_kunnat'].split(' / ')
                    if len(alt_name) == 1:
                        value = alt_name[0]
                    else:
                        value = alt_name[1]
                    liter = Literal(value)
                elif column_name.startswith('kuva_') and not column_name.endswith('kuvaajan_nimi'):
                    ph = column_name[0:6] + '_kuvaajan_nimi'
                    photographer = row[ph]
                    photo_club = row['kuvaukset_toteuttanut_kameraseura']
                    cemetery_id = format(row['nro'], '03d')
                    photo_number = '0' + column_name[5]
                    caption = column_name[7:].replace('_', ' ').capitalize()
                    self.create_photograph_and_photography_event_instances(value, photographer, photo_club, cemetery_id,
                                                                           entity_uri, photo_number, caption)
                elif column_name.endswith('kuvaajan_nimi'):
                    liter = None
                else:
                    liter = Literal(value)

                if column_name == 'nykyiset_kunnat':
                    row_rdf.add((entity_uri, mapping['uri'], narc_name))
                    row_rdf.add((entity_uri, mapping['uri2'], current_municipality))
                    if former_municipality:
                        row_rdf.add((entity_uri, mapping['uri3'], former_municipality))
                elif liter:
                    row_rdf.add((entity_uri, mapping['uri'], liter))

            if row_rdf:
                row_rdf.add((entity_uri, RDF.type, self.instance_class))
            else:
                # Don't create class instance if there is no data about it
                logging.debug('No data found for {uri}'.format(uri=entity_uri))

        return row_rdf

    def create_photograph_and_photography_event_instances(self, filename, photographer, photo_club, cemetery_id,
                                                          cemetery_uri, photo_number, caption):
        photo_rdf = Graph()

        photo_uri = CEMETERY_PHOTO_NS['cemetery_photo_' + cemetery_id + '_' + photo_number]
        photography_uri = EVENTS_NS['cemetery_photo_' + cemetery_id + '_' + photo_number]

        photo_rdf.add((photo_uri, RDF.type, WARSA_PHOTOGRAPHS_NS['Photograph']))
        photo_rdf.add((photo_uri, CIDOC.P138_represents, cemetery_uri))
        photo_rdf.add((photo_uri, DC.description, Literal(caption, 'fi')))
        photo_rdf.add((photo_uri, SCHEMA_ORG.contentUrl,
                       Literal('http://static.sotasampo.fi/photographs/cemeteries/3000x2000px/' + filename)))
        photo_rdf.add((photo_uri, SCHEMA_ORG.thumbnailUrl,
                       Literal('http://static.sotasampo.fi/photographs/cemeteries/300x200px/_p_' + filename)))

        photo_rdf.add((photography_uri, RDF.type, WARSA_EVENT_TYPES_NS['Photography']))
        photo_rdf.add((photography_uri, CIDOC.P94_has_created, photo_uri))
        photo_rdf.add((photography_uri, CIDOC.P14_carried_out_by, Literal(photographer)))

        self.photographs += photo_rdf

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

    def serialize(self, destination_data, destination_photographs, destination_schema):
        """
        Serialize RDF graphs

        :param destination_data: serialization destination for data
        :param destination_photographs: serialization destination for photo data
        :param destination_schema: serialization destination for schema
        :return: output from rdflib.Graph.serialize
        """
        self.data.bind("cemeteries_temp", "http://ldf.fi/warsa/temp/")
        self.data.bind("cemeteries_schema", "http://ldf.fi/schema/warsa/cemeteries/")
        self.data.bind("skos", "http://www.w3.org/2004/02/skos/core#")
        self.data.bind("crm", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.data.bind("foaf", 'http://xmlns.com/foaf/0.1/')
        self.data.bind("bioc", 'http://ldf.fi/schema/bioc/')

        self.photographs.bind("crm", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.photographs.bind("schema", 'http://schema.org/')
        self.photographs.bind("cemeteries_temp", "http://ldf.fi/warsa/temp/")
        self.photographs.bind("photos", "http://ldf.fi/warsa/photographs/")
        self.photographs.bind("cphotos", "http://ldf.fi/warsa/photographs/cemeteries/")
        self.photographs.bind("events", "http://ldf.fi/warsa/events/")
        self.photographs.bind("event_types", "http://ldf.fi/warsa/events/event_types/")

        self.schema.bind("cemeteries_schema", "http://ldf.fi/schema/warsa/cemeteries/")
        self.schema.bind("skos", "http://www.w3.org/2004/02/skos/core#")
        self.schema.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.schema.bind("foaf", 'http://xmlns.com/foaf/0.1/')
        self.schema.bind("bioc", 'http://ldf.fi/schema/bioc/')

        data = self.data.serialize(format="turtle", destination=destination_data)
        photographs = self.photographs.serialize(format="turtle", destination=destination_photographs)
        schema = self.schema.serialize(format="turtle", destination=destination_schema)

        self.log.info('Data serialized to %s' % destination_data)
        self.log.info('Photo data serialized to %s' % destination_photographs)
        self.log.info('Schema serialized to %s' % destination_schema)

        return data, photographs, schema  # Return for testing purposes

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

        mapper.serialize(output_dir + "cemeteries-temp.ttl", output_dir + "cemeteries-photographs.ttl",
                         output_dir + "cemeteries-schema.ttl")

    

