#!/usr/bin/env python
# Author
# License

import urllib.request
from urllib.error import HTTPError
import re
import xml.etree.ElementTree as ET
import html
import sys
import datetime


# catalog of life scientific name search
# queries catalog of life with a scientific name
# returns the most up-to-date, accepted, scientific name for a specimen
# or an error message to calling function
def colNameSearch(givenScientificName):
    identification = str(givenScientificName).split()
    if givenScientificName != '':
        identQuery = [identification[0]]
    # no sci-name in row
    else:
        return 'empty_string'
    if len(identification) > 1:
        identQuery.append(identification[1])
        if len(identification) > 2:
            identQuery.append(identification[-1])
    try:
        CoLQuery = ET.parse(urllib.request.urlopen('http://webservice.catalogueoflife.org/col/webservice?name={}&response=terse'.format('+'.join(identQuery)), timeout=30)).getroot()
    # help(socket.timeout)
    except OSError:
        try:
            # This try attempt tries to load a catalog by specififying the current year
            # We may want to ask the user first, or consider removing this.
            # This tries  the current year then attempts a year prior before giving up.
            print('useing the alternative CoL URL')
            CoLQuery = ET.parse(urllib.request.urlopen('http://webservice.catalogueoflife.org/annual-checklist/{}/webservice?name={}&response=terse'.format(datetime.datetime.now().year,'+'.join(identQuery)), timeout=30)).getroot()
        # help(socket.timeout)
        except OSError:
            try:
                CoLQuery = ET.parse(urllib.request.urlopen('http://webservice.catalogueoflife.org/annual-checklist/{}/webservice?name={}&response=terse'.format(datetime.datetime.now().year -1 ,'+'.join(identQuery)), timeout=30)).getroot()
            except HTTPError:
                return 'http_Error'
    #<status>accepted name|ambiguous synonym|misapplied name|privisionally acceptedname|synomym</status>  List of potential name status

    #Check if CoL returned an Error
    if len(CoLQuery.get('error_message')) > 0:
        return ('ERROR', str(CoLQuery.get('error_message')))
    #if not an error, then pull all the results
    for result in CoLQuery.findall('result'):
    #start checking the results for the first instance of an accepted name.
        nameStatus = result.find('name_status').text
        if nameStatus == 'accepted name':
            name = result.find('name').text
            try: #Try to locate an instance in which the name is italicized (because CoL returns an HTML name with authority)
                authorityName = result.find('name_html').find('i').tail
            except AttributeError:
                try:
                    # Try another method to find the HTML name with authority
                    authorityName = html.unescape(result.find('name_html').text)
                    authorityName = authorityName.split('</i> ')[1]
                except IndexError:
                    # Give up looking for authority
                    authorityName = ''
                #cleaning the author name up.
            authorityName = re.sub(r'\d+','',str(authorityName))
            authorityName = authorityName.strip().rstrip(',')
            return (name,authorityName)
        elif 'synonym' in nameStatus:
            return colNameSearch(result.find('accepted_name/name').text)
