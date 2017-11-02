#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Mapping of CSV columns to RDF properties
"""

from converters import add_trailing_zeros, parse_coordinate, split_cemetery_name, convert_int, convert_dates
from namespaces import *

CEMETERY_MAPPING = {
    #'onko': {'uri': WARSA_CEMETERY_SCHEMA_NS.status,
    #         'name_fi': 'Onko hautausmaa'},
    'tyyppi': {'uri': CEMETERY_SCHEMA_NS.cemetery_type,
               'name_fi': 'Hautausmaan tyyppi',
               'name_en': 'Cemetery type'},
    'nro': {'uri': CEMETERY_SCHEMA_NS.cemetery_id,
            'converter': add_trailing_zeros,
            'name_fi': 'Hautausmaan tunniste',
            'name_en': 'Cemetery identifier'},
    'nykyiset_kunnat': {'current_municipality_uri': CEMETERY_SCHEMA_NS.current_municipality,
                        'former_municipality_uri': CEMETERY_SCHEMA_NS.former_municipality,
                        'original_narc_name_uri': CEMETERY_SCHEMA_NS.original_narc_name,
                        'converter': split_cemetery_name,
                        'current_municipality_name_fi': 'Nykyinen kunta',
                        'former_municipality_name_fi': 'Entinen kunta',
                        'current_municipality_name_en': 'Current municipality',
                        'former_municipality_name_en': 'Former municipality'},
    'kuvaukset_toteuttanut_kameraseura': {'uri': CEMETERY_SCHEMA_NS.camera_club,
                                          'name_fi': 'Kuvaukset toteuttanut kameraseura',
                                          'name_en': 'Camera club'},
    'hautausmaan_nimi': {'uri': SKOS.prefLabel},
    'arkkitehti': {'uri': CEMETERY_SCHEMA_NS.architect,
                   'name_fi': 'Arkkitehti',
                   'name_en': 'Architect'},
    'hautoja': {'uri': CEMETERY_SCHEMA_NS.number_of_graves,
                   'converter': convert_int,
                   'name_fi': 'Hautojen lukumäärä',
                   'name_en': 'Number of graves'},
    'perustettu': {'uri': CEMETERY_SCHEMA_NS.date_of_foundation,
                   'converter': convert_dates,
                   'name_fi': 'Perustamisvuosi',
                   'name_en': 'Date of foundation'},
    'paljastettu': {'uri': CEMETERY_SCHEMA_NS.memorial_unveiling_date,
                   'converter': convert_dates,
                   'name_fi': 'Muistimerkin paljastamisaika',
                   'name_en': 'Memorial unveiling date'},
    'nimi': {'uri': CEMETERY_SCHEMA_NS.memorial,
                   'name_fi': 'Muistomerkin nimi',
                   'name_en': 'Memorial'},
    'kuvanveistäjä': {'uri': CEMETERY_SCHEMA_NS.memorial_sculptor,
                   'name_fi': 'Kuvanveistäjä',
                   'name_en': 'Sculptor'},
    'pituus_n': {'uri': WGS84.lat,
                 'converter': parse_coordinate},
    'leveys_e': {'uri': WGS84.long,
                 'converter': parse_coordinate},
    'tarkka_katuosoite': {'uri': CEMETERY_SCHEMA_NS.address,
                   'name_fi': 'Osoite',
                   'name_en': 'Address'},

    'kuva_1_yleiskuva_sankarihautausmaasta': {},
    'kuva_1_kuvaajan_nimi': {},
    'kuva_2_yksittäinen_hauta_risteineen_muistolaattoineen': {},
    'kuva_2_kuvaajan_nimi': {},
    'kuva_3_muistomerkki': {},
    'kuva_3_kuvaajan_nimi': {},
    'kuva_4_yleiskuva': {},
    'kuva_4_kuvaajan_nimi': {},
    'kuva_5_muu_muistomerkki': {},
    'kuva_5_kuvaajan_nimi': {},




}
