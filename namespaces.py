#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Define common RDF namespaces
"""
from rdflib import Namespace, RDF, RDFS, XSD

CIDOC = Namespace('http://www.cidoc-crm.org/cidoc-crm/')
DC = Namespace('http://purl.org/dc/terms/')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
BIOC = Namespace('http://ldf.fi/schema/bioc/')
WGS84 = Namespace('http://www.w3.org/2003/01/geo/wgs84_pos#')
SCHEMA_ORG = Namespace('http://schema.org/')

# warsa schemas
WARSA_SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/')
CEMETERY_SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/places/cemeteries/')
PHOTOGRAPH_SCHEMA_NS = Namespace('http://ldf.fi/schema/warsa/photographs/')

# warsa data namespaces
CEMETERY_DATA_NS = Namespace('http://ldf.fi/warsa/places/cemeteries/') 
DATA_NS = Namespace('http://ldf.fi/warsa/temp/')
EVENTS_NS = Namespace('http://ldf.fi/warsa/events/')
# CEMETERY_PHOTO_NS = Namespace('http://ldf.fi/warsa/photographs/cemeteries/')
WARSA_PHOTOGRAPHS_NS = Namespace('http://ldf.fi/warsa/photographs/')
WARSA_MEDIA_NS = Namespace('http://ldf.fi/warsa/media/')
WARSA_SOURCE_NS = Namespace('http://ldf.fi/warsa/sources/')
