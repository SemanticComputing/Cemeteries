#!/usr/bin/env python3
#  -*- coding: UTF-8 -*-
"""
Converters for CSV cell data
"""

import datetime
import logging
import re

from rdflib import Graph, Literal
from slugify import slugify

from namespaces import *

log = logging.getLogger(__name__)


def convert_int(raw_value: str):
    """
    Convert string value to integer if possible, if not, return original value

    :param raw_value: original string value
    :return: converted or original value
    """
    if not raw_value:
        return raw_value
    try:
        value = int(raw_value)  # This cannot be directly converted on the DataFrame because of missing values.
        log.debug('Converted int: %s' % raw_value)
        return value
    except (ValueError, TypeError):
        log.warning('Invalid value for int conversion: %s' % raw_value)
        return raw_value


def convert_dates(raw_date: str):
    """
    Convert date string to iso8601 date

    :param raw_date: raw date string from the CSV
    :return: ISO 8601 compliant date if can be parse, otherwise original date string
    """
    if not raw_date:
        return raw_date
    try:
        date = datetime.datetime.strptime(str(raw_date).strip(), '%d/%m/%Y').date()
        log.debug('Converted date: %s  to  %s' % (raw_date, date))
        return date
    except ValueError:
        try:
            date = datetime.datetime.strptime(str(raw_date).strip(), '%d.%m.%Y').date()
            log.debug('Converted date: %s  to  %s' % (raw_date, date))
            return date
        except ValueError:
            log.warning('Invalid value for date conversion: %s' % raw_date)
        return raw_date


def convert_person_name(raw_name: str):
    """
    Unify name syntax and split into first names and last name

    :param raw_name: Original name string
    :return: tuple containing first names, last name and full name
    """
    re_name_split = \
        r'([A-ZÅÄÖÜÉÓÁ/\-]+(?:\s+\(?E(?:NT)?[\.\s]+[A-ZÅÄÖÜÉÓÁ/\-]+)?\)?)\s*(?:(VON))?,?\s*([A-ZÅÄÖÜÉÓÁ/\- \(\)0-9,.]*)'

    fullname = raw_name.upper()

    namematch = re.search(re_name_split, fullname)
    (lastname, extra, firstnames) = namematch.groups() if namematch else (fullname, None, '')

    # Unify syntax for previous names
    prev_name_regex = r'([A-ZÅÄÖÜÉÓÁ/\-]{2}) +\(?(E(?:NT)?[\.\s]+)([A-ZÅÄÖÜÉÓÁ/\-]+)\)?'
    lastname = re.sub(prev_name_regex, r'\1 (ent. \3)', str(lastname))

    lastname = lastname.title().replace('(Ent. ', '(ent. ')
    firstnames = firstnames.title()

    if extra:
        extra = extra.lower()
        lastname = ' '.join([extra, lastname])

    fullname = lastname

    if firstnames:
        fullname += ', ' + firstnames

    log.debug('Name %s was unified to form %s' % (raw_name, fullname))

    original_style_name = ' '.join((lastname, firstnames)) if firstnames else lastname
    if original_style_name.lower() != raw_name.lower():
        log.warning('New name %s differs from %s' % (original_style_name, raw_name))

    return firstnames, lastname, fullname


def create_event(uri_suffix, event_type, participant_prop, participant, participant_name, labels, timespan=None,
                 place=None, prop_sources=None, extra_information=None):
    """
    Create an event or add information to an existing one (by using a previously used URI).

    :param uri_suffix:
    :param event_type: URIRef
    :param participant_prop:
    :param participant:
    :param participant_name:
    :param labels: list of label literals in different languages
    :param timespan: timespan tuple (begin, end) or single date
    :param place: string representing the target place
    :param prop_sources:
    :param extra_information: list of (predicate, object) tuples
    """

    event = Graph()

    uri = EVENTS_NS[uri_suffix]
    event.add((uri, RDF.type, event_type))
    event.add((uri, participant_prop, participant))

    labels = (Literal(labels[0].format(name=participant_name), lang='fi'),
              Literal(labels[1].format(name=participant_name), lang='en'))

    for label in labels:
        event.add((uri, SKOS.prefLabel, label))

    # if event_source:
    #     event.add((uri, DC.source, event_source))

    if extra_information:
        for info in extra_information:
            event.add((uri,) + info)

    if timespan:
        if type(timespan) != tuple:
            timespan = (timespan, timespan)

        timespan_uri = EVENTS_NS[uri_suffix + '_timespan']
        label = (timespan[0] + ' - ' + timespan[1]) if timespan[0] != timespan[1] else timespan[0]

        event.add((uri, CIDOC['P4_has_time-span'], timespan_uri))
        event.add((timespan_uri, RDF.type, CIDOC['E52_Time-Span']))
        event.add((timespan_uri, CIDOC.P82a_begin_of_the_begin, Literal(timespan[0], datatype=XSD.date)))
        event.add((timespan_uri, CIDOC.P82b_end_of_the_end, Literal(timespan[1], datatype=XSD.date)))
        event.add((timespan_uri, SKOS.prefLabel, Literal(label)))

        if prop_sources:
            for timespan_source in prop_sources:
                event.add((timespan_uri, DC.source, timespan_source))

    if place:
        property_uri = CIDOC['P7_took_place_at']
        event.add((uri, property_uri, place))

        if prop_sources:
            # TODO: Use singleton properties or PROV Ontology (https://www.w3.org/TR/prov-o/#qualifiedAssociation)
            for place_source in prop_sources:
                # USING (SEMI-)SINGLETON PROPERTIES TO DENOTE SOURCE
                property_uri = DATA_NS['took_place_at_' + slugify(place) + '_' + slugify(place_source)]

                event.add((property_uri, DC.source, place_source))
                event.add((property_uri, RDFS.subClassOf, CIDOC['P7_took_place_at']))

    return event


def strip_dash(raw_value: str):
    return '' if raw_value.strip() == '-' else raw_value


def add_trailing_zeros(raw_value):
    i = convert_int(raw_value)
    return format(i, '03d')


# http://en.proft.me/2015/09/20/converting-latitude-and-longitude-decimal-values-p/
def dms2dd(degrees, minutes, seconds, direction):
    dd = float(degrees) + float(minutes)/60 + float(seconds)/(60*60);
    dd = round(dd, 8)
    if direction == 'S' or direction == 'W':
        dd *= -1
    #print('converted: ' + str(dd))
    return dd


def dd2dms(deg):
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return [d, m, sd]


def parse_coordinate(raw_value):

    if raw_value == '' or raw_value == 'ei_ole' :
        return None

    # Convert xx.xx.xx.x to xx°xx'xx"

    # strip whitespace
    raw_value = "".join(raw_value.split())


    if raw_value[2] == '.' or raw_value[2].isspace() or raw_value[2] == ',':
        modified = list(raw_value)

        # remove double periods
        if modified[-1] == '.' and modified[-2] == '.':
            modified = modified[:-2]

        # remove periods from end
        if modified[-1] == '.':
            modified = modified[:-1]

        modified[2] = u"\u00B0"
        modified[5] = '\''
        modified += '\"'
        new_value = "".join(modified)
    else:
        return None

    # Add direction
    if not new_value.endswith(' N') and int(new_value[0:2]) > 59:
        raw_value += ' N'
    elif not new_value.endswith(' E') and int(new_value[0:2]) < 30:
        new_value += ' E'

    # parts = re.split('[^\d\w]+', dms)
    parts = re.split('[^\d\w\.]+', str(new_value))
    #print('original: ' + str(raw_value))

    # remove double periods from seconds
    if parts[2].count('.') > 1:
        oldstr = parts[2]
        newstr = oldstr[:3] + oldstr[4:]
        parts[2] = newstr

    return dms2dd(parts[0], parts[1], parts[2], parts[3])

def split_cemetery_name(raw_value):

    parts = raw_value.split(' / ')
    if len(parts) == 1:
        # no former municipality
        former_municipality = None
        # municipality, name of the cemetery etc
        current_municipality = raw_value.split(',')[0]
        narc_name = raw_value
    #else isinstance(parts, list):
    else:
        current_municipality = parts[0]
        former_municipality = parts[1].split(',')[0]
        narc_name = parts[1]
    #else:
#        current_municipality = parts.split(',')[0]
        # if the municipality has not changed, should we add both
        # former and current municipality?
#        former_municipality = None
#        narc_name = value)

    return { 'current_municipality': current_municipality,
        'former_municipality': former_municipality,
        'narc_name': narc_name }
