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
import csv
from converters import split_cemetery_name
from pathlib import Path

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
        self.information_objects = Graph()
        self.schema = Graph()
        self.narc_names = {}
        self.new_cemetery_id = 923
        self.photo_counter = 0
        self.cemeteries_from_project = 0
        self.cemeteries_in_warsampo_not_project = 0
        self.cemeteries_new_to_warsampo = 0
        self.cemeteries_already_in_warsampo = 0
        self.cemeteries_found_in_warsampo = 0
        self.missing_filenames = []
        self.missing_filename_columns = []
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
        casualties_source_uri = WARSA_SOURCE_NS['source9']
        photo_project_source_uri = WARSA_SOURCE_NS['source21']

        # Loop through the mapping dict and convert data to RDF
        for column_name in self.mapping:

            mapping = self.mapping[column_name]

            value = row[column_name]

            if column_name == 'hautausmaan_nimi':
                names = split_cemetery_name(row['nykyiset_kunnat'])
                if (value == 'ei_ole' or value == ''):
                    value = names['narc_name']
                else:
                    value = names['current_municipality'] + ', ' + value


            if value == 'ei_ole' or value == 'ei ole' or value == '':
                # print(value)
                continue

            converter = mapping.get('converter')
            value = converter(value) if converter else value

            # if column_name == 'nro':
                # print(value)

            # gather info into these variables
            liter = None
            current_municipality = None
            former_municipality = None
            narc_name = None
            number_of_graves_string = None
            number_of_graves_int = None

            if column_name == 'pituus_n' or column_name == 'leveys_e':
                if value:
                    liter = Literal(value, datatype=XSD.float)
            # nykyiset_kunnat column is split into three properties
            elif column_name == 'nykyiset_kunnat':
                current_municipality = Literal(value['current_municipality'])
                if value['former_municipality']:
                    former_municipality = Literal(value['former_municipality'])
                narc_name = Literal(value['narc_name'])
            # collect all photo info and create photograph and photography instances
            elif column_name.startswith('kuva_') and not column_name.endswith('kuvaajan_nimi'):
                ph = column_name[0:6] + '_kuvaajan_nimi'
                photographer = row[ph]
                photo_club = row['kuvaukset_toteuttanut_kameraseura']
                cemetery_id = format(row['nro'], '03d')
                photo_number = '0' + column_name[5]
                caption_fi = column_name[7:].replace('_', ' ').capitalize()
                # print(caption_fi)
                if caption_fi == "Yleiskuva sankarihautausmaasta":
                    caption_en = "Panorama of the cemetery"
                elif caption_fi == "Muistomerkki":
                    caption_en = "Memorial"
                elif caption_fi == "Yksittäinen hauta risteineen muistolaattoineen":
                    caption_en = "Single grave with a cross and a brass"
                elif caption_fi == "Muu muistomerkki":
                    caption_en = "Other memorial"
                elif caption_fi == "Yleiskuva":
                    caption_en = "Panorama of the area"

                # check if photo files exist
                big_photo = Path('/m/cs/project/sotasampo-public/photographs/cemeteries/3000x2000px/' + value)
                small_photo = Path('/m/cs/project/sotasampo-public/photographs/cemeteries/300x200px/' + value)
                #big_photo = Path('/esko-local-files/hautausmaat/3000x2000px/' + value)
                #small_photo = Path('esko-local-files/hautausmaat/300x200px/' + value)

                #if not big_photo.is_file():
                #    self.missing_filenames.append(value)
                    #self.missing_filenames.append('3000x2000px/' + value)

                #if not small_photo.is_file():
                    #self.missing_filenames.append(value)
                    #self.missing_filenames.append('300x200px/' + value)

                self.create_photograph_and_photography_event_instances(value,
                photographer, photo_club, cemetery_id, entity_uri, photo_number, caption_fi, caption_en)
            elif column_name.endswith('kuvaajan_nimi'):
                liter = None
            elif column_name == 'hautoja':
                if isinstance(value, int ):
                    number_of_graves_int = value
                else:
                    number_of_graves_string = value
            else:
                liter = Literal(value)

            # create RDF data
            if column_name == 'nykyiset_kunnat':
                row_rdf.add((entity_uri, mapping['current_municipality_uri'], current_municipality))
                row_rdf.add((entity_uri, mapping['original_narc_name_uri'], narc_name))
                if former_municipality and former_municipality != None:
                    row_rdf.add((entity_uri, mapping['former_municipality_uri'], former_municipality))
            elif column_name == 'hautoja':
                if number_of_graves_int != None:
                    row_rdf.add((entity_uri, mapping['uri'], Literal(number_of_graves_int, datatype=XSD.integer)))
                else:
                    row_rdf.add((entity_uri, mapping['uri'], Literal(number_of_graves_string)))
            elif liter:
                #print(mapping)
                row_rdf.add((entity_uri, mapping['uri'], liter))

            if row_rdf:
                row_rdf.add((entity_uri, RDF.type, self.instance_class))
                # cemetery data is based on two sources
                row_rdf.add((entity_uri, DC.source, photo_project_source_uri))
                row_rdf.add((entity_uri, DC.source, casualties_source_uri))

            else:
                # Don't create class instance if there is no data about it
                logging.debug('No data found for {uri}'.format(uri=entity_uri))


        return row_rdf

    def create_photograph_and_photography_event_instances(self, filename, photographer, photo_club, cemetery_id,
                                                          cemetery_uri, photo_number, caption_fi, caption_en):

        # URIs
        lg_uri = WARSA_MEDIA_NS['cemetery_photo_lg_' + cemetery_id + '_' + photo_number]
        sm_uri = WARSA_MEDIA_NS['cemetery_photo_sm_' + cemetery_id + '_' + photo_number]
        photo_uri = WARSA_PHOTOGRAPHS_NS['cemetery_photo_' + cemetery_id + '_' + photo_number]
        photography_uri = EVENTS_NS['cemetery_photo_' + cemetery_id + '_' + photo_number]
        photo_project_source_uri = WARSA_SOURCE_NS['source21']

        # create information objects
        io_rdf = Graph()
        io_rdf.add((lg_uri, SCHEMA_ORG.contentUrl,
                       Literal('https://static.sotasampo.fi/photographs/cemeteries/3000x2000px/' + filename)))
        io_rdf.add((lg_uri, CIDOC.P138_represents, photo_uri))
        io_rdf.add((lg_uri, RDF.type, CIDOC.E73_Information_Object))
        io_rdf.add((lg_uri, SKOS.prefLabel, Literal('Full size', 'en')))
        io_rdf.add((lg_uri, SKOS.prefLabel, Literal('Suuri', 'fi')))
        io_rdf.add((lg_uri, PHOTOGRAPH_SCHEMA_NS.size, PHOTOGRAPH_SCHEMA_NS.lg))

        io_rdf.add((sm_uri, SCHEMA_ORG.contentUrl,
                       Literal('https://static.sotasampo.fi/photographs/cemeteries/300x200px/' + filename)))
        io_rdf.add((sm_uri, CIDOC.P138_represents, photo_uri))
        io_rdf.add((sm_uri, RDF.type, CIDOC.E73_Information_Object))
        io_rdf.add((sm_uri, SKOS.prefLabel, Literal('Thumbnail', 'en')))
        io_rdf.add((sm_uri, SKOS.prefLabel, Literal('Pieni', 'fi')))
        io_rdf.add((sm_uri, PHOTOGRAPH_SCHEMA_NS.size, PHOTOGRAPH_SCHEMA_NS.sm))

        self.information_objects += io_rdf

        # create :Photogaph and :Photography instances
        photo_rdf = Graph()
        photo_rdf.add((photo_uri, RDF.type, WARSA_SCHEMA_NS['Photograph']))
        photo_rdf.add((photo_uri, CIDOC.P138_represents, cemetery_uri))
        photo_rdf.add((photo_uri, CIDOC.P138i_has_representation, lg_uri))
        photo_rdf.add((photo_uri, CIDOC.P138i_has_representation, sm_uri))
        photo_rdf.add((photo_uri, DC.description, Literal(caption_fi, 'fi')))
        photo_rdf.add((photo_uri, DC.description, Literal(caption_en, 'en')))
        photo_rdf.add((photo_uri, DC.source, photo_project_source_uri))


        photo_rdf.add((photography_uri, RDF.type, WARSA_SCHEMA_NS['Photography']))
        photo_rdf.add((photography_uri, CIDOC.P94_has_created, photo_uri))
        photo_rdf.add((photography_uri, CIDOC.P14_carried_out_by, Literal(photographer)))
        photo_rdf.add((photography_uri, DC.source, photo_project_source_uri))

        self.photographs += photo_rdf
        self.photo_counter += 1

    def read_csv(self, csv_input):
        """
        Read in a CSV files using pandas.read_csv

        :param csv_input: CSV input (filename or buffer)
        """
        csv_data = pd.read_csv(csv_input, encoding='UTF-8', index_col=False, sep=';', quotechar='"',
                               # parse_dates=[1], infer_datetime_format=True, dayfirst=True,
                               na_values=[' '],
                               #converters={'ammatti': lambda x: x.lower()}
                               )

        self.table = csv_data.fillna('').applymap(lambda x: x.strip() if type(x) == str else x)
        self.log.info('Data read from CSV %s' % csv_input)

    def read_narc_cemetery_uris_from_csv(self):
        reader = csv.DictReader(open('cemetery-uris-labels-narc.csv'))
        for row in reader:
            label = row.pop('original_narc_name').rstrip()
            key = label.lower()

            # Kokemäki was the only duplicate label in narc listing,
            # manually renamed to Kokemäki 3 csv
            #if key in self.narc_names:
            #    # ignore duplicate label
            #    print(key)
            #    pass

            uri = row.pop('uri').rstrip()
            self.narc_names[key] = (uri, label)
        self.cemeteries_already_in_warsampo = len(self.narc_names.keys())

    def create_extra_cemeteries(self, cemeteries):
        cemetery_rdf = Graph()
        for key in cemeteries:
            cemetery_uri = URIRef(cemeteries[key][0])
            cemetery_rdf.add((cemetery_uri, RDF.type, self.instance_class))
            cemetery_rdf.add((cemetery_uri, SKOS.prefLabel, Literal(cemeteries[key][1])))
        return cemetery_rdf

    def serialize(self, destination_data, destination_photographs, destination_ios, destination_schema):
        """
        Serialize RDF graphs

        :param destination_data: serialization destination for data
        :param destination_photographs: serialization destination for photo data
        :param destination_schema: serialization destination for schema
        :return: output from rdflib.Graph.serialize
        """
        self.data.bind("temp-cemetery", "http://ldf.fi/warsa/temp/")
        self.data.bind("skos", "http://www.w3.org/2004/02/skos/core#")
        self.data.bind("crm", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.data.bind("foaf", 'http://xmlns.com/foaf/0.1/')
        self.data.bind("bioc", 'http://ldf.fi/schema/bioc/')
        self.data.bind("wgs84", 'http://www.w3.org/2003/01/geo/wgs84_pos#')
        self.data.bind("", "http://ldf.fi/schema/warsa/")
        self.data.bind("wces", "http://ldf.fi/schema/warsa/places/cemeteries/")
        self.data.bind("wce", 'http://ldf.fi/warsa/places/cemeteries/')
        self.data.bind("wso", "http://ldf.fi/warsa/sources/")
        self.data.bind("dc-terms", "http://purl.org/dc/terms/")

        self.photographs.bind("crm", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.photographs.bind("schema", 'http://schema.org/')
        self.photographs.bind("dc-terms", "http://purl.org/dc/terms/")
        self.photographs.bind("", "http://ldf.fi/schema/warsa/")
        self.photographs.bind("temp-cemetery", "http://ldf.fi/warsa/temp/")
        self.photographs.bind("wph", "http://ldf.fi/warsa/photographs/")
        self.photographs.bind("wev", "http://ldf.fi/warsa/events/")
        self.photographs.bind("wso", "http://ldf.fi/warsa/sources/")

        self.information_objects.bind("skos", "http://www.w3.org/2004/02/skos/core#")
        self.information_objects.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.information_objects.bind("schema", 'http://schema.org/')
        self.information_objects.bind("wphs", 'http://ldf.fi/schema/warsa/photographs/')
        self.information_objects.bind("wme", 'http://ldf.fi/warsa/media/')

        self.schema.bind("", "http://ldf.fi/schema/warsa/")
        self.schema.bind("skos", "http://www.w3.org/2004/02/skos/core#")
        self.schema.bind("cidoc", 'http://www.cidoc-crm.org/cidoc-crm/')
        self.schema.bind("foaf", 'http://xmlns.com/foaf/0.1/')
        self.schema.bind("bioc", 'http://ldf.fi/schema/bioc/')

        data = self.data.serialize(format="turtle", destination=destination_data)
        photographs = self.photographs.serialize(format="turtle", destination=destination_photographs)
        information_objects = self.information_objects.serialize(format="turtle", destination=destination_ios)
        schema = self.schema.serialize(format="turtle", destination=destination_schema)

        self.log.info('Data serialized to %s' % destination_data)
        self.log.info('Photo data serialized to %s' % destination_photographs)
        self.log.info('Information object data serialized to %s' % destination_ios)
        self.log.info('Schema serialized to %s' % destination_schema)

        return data, photographs, information_objects, schema  # Return for testing purposes

    def process_rows(self):
        """
        Loop through CSV rows and convert them to RDF
        """
        # column_headers = list(self.table)
        #
        for index in range(len(self.table)):



            # convert to RDF
            if self.table.ix[index]['tyyppi'] != 'ei_ole':

                # create an URI
                names = split_cemetery_name(self.table.ix[index]['nykyiset_kunnat'])
                photo_project_name = names['narc_name'].lower()
                if photo_project_name in self.narc_names:
                    cemetery_uri = URIRef(self.narc_names[photo_project_name][0])
                    del self.narc_names[photo_project_name]
                    self.cemeteries_found_in_warsampo += 1
                else:
                    # create new URIs for cemeteries that are not already in WarSampo
                    local_name = 'h0' + str(self.new_cemetery_id) + '_1'
                    self.new_cemetery_id += 1
                    cemetery_uri = CEMETERY_DATA_NS[local_name]
                    self.cemeteries_new_to_warsampo += 1
                    #print(cemetery_uri)
                    #print(photo_project_name)

                row_rdf = self.map_row_to_rdf(cemetery_uri, self.table.ix[index])

            if row_rdf:
                self.data += row_rdf

        #print(self.cemeteries_found_in_warsampo)
        #print(self.cemeteries_new_to_warsampo)

        self.log.info('Photos created: %s' % self.photo_counter)
        #print(len(self.missing_filenames))
        #print(len(self.missing_filename_columns))
        for filename in self.missing_filenames:
           print(filename)
        #for column in self.missing_filename_columns:
         #  print(column)

        # Generate simple cemeteries with no metadata from the leftover
        # cemeteries that were not found in the photography project
        self.cemeteries_in_warsampo_not_project = len(self.narc_names.keys())
        self.data += self.create_extra_cemeteries(self.narc_names)

        total_found = self.cemeteries_found_in_warsampo + self.cemeteries_new_to_warsampo

        self.log.info('cemeteries already in WarSampo: %s' % self.cemeteries_already_in_warsampo)
        self.log.info('cemeteries found in WarSampo: %s' % self.cemeteries_found_in_warsampo)
        self.log.info('cemeteries new to WarSampo: %s' % self.cemeteries_new_to_warsampo)
        self.log.info('total cemeteries found in the project: %s' % str(total_found))
        self.log.info('cemeteries in Warsampo but not found in the project: %s' % self.cemeteries_in_warsampo_not_project)

        # generate schema RDF
        for prop in CEMETERY_MAPPING.values():

            if 'uri' in prop:
                self.schema.add((prop['uri'], RDF.type, RDF.Property))
                if 'name_fi' in prop:
                    self.schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_fi'], lang='fi')))
                if 'name_en' in prop:
                    self.schema.add((prop['uri'], SKOS.prefLabel, Literal(prop['name_en'], lang='en')))
            # special case: nykyiset_kunnat column is split into three properties
            elif 'current_municipality_uri' in prop:
                self.schema.add((prop['current_municipality_uri'], RDF.type, RDF.Property))
                self.schema.add((prop['current_municipality_uri'], SKOS.prefLabel,
                                 Literal(prop['current_municipality_name_fi'], lang='fi')))
                self.schema.add((prop['current_municipality_uri'], SKOS.prefLabel,
                                 Literal(prop['current_municipality_name_en'], lang='en')))

                self.schema.add((prop['former_municipality_uri'], RDF.type, RDF.Property))
                self.schema.add((prop['former_municipality_uri'], SKOS.prefLabel,
                                 Literal(prop['former_municipality_name_fi'], lang='fi')))
                self.schema.add((prop['former_municipality_uri'], SKOS.prefLabel,
                                 Literal(prop['former_municipality_name_en'], lang='en')))
            else:
                continue

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
        mapper = RDFMapper(CEMETERY_MAPPING, WARSA_SCHEMA_NS['Cemetery'], loglevel=args.loglevel.upper())
        mapper.read_narc_cemetery_uris_from_csv()
        mapper.read_csv(args.input)
        mapper.process_rows()
        mapper.serialize(output_dir + "cemeteries.ttl", output_dir + "cemetery_photos_and_photography_events.ttl",
                         output_dir + "cemetery-photo-media.ttl", output_dir + "cemeteries-schema.ttl")
