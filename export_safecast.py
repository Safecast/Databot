#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright (C) 2013 Lionel Bergeret
#
# ----------------------------------------------------------------
# The contents of this file are distributed under the CC0 license.
# See http://creativecommons.org/publicdomain/zero/1.0/
# ----------------------------------------------------------------

# system libraries
import os, sys
import time, traceback
from datetime import datetime
from optparse import OptionParser
import glob

from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2

# Register the streaming http handlers with urllib2
register_openers()

# -----------------------------------------------------------------------------
# Simple options object (compatible with OptionParser)
# -----------------------------------------------------------------------------
class Options:
    attr = {}
    def __setitem__(self, key, value):
       self.attr[key] = value
    def __getitem__(self, key):
       return self.attr[key]

# -----------------------------------------------------------------------------
# Log print
# -----------------------------------------------------------------------------
def logPrint(message):
   print datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message

# -----------------------------------------------------------------------------
# Safecast API class for uploading logs
# -----------------------------------------------------------------------------
class SafecastAPI:
    def __init__(self, apikey = "JpwWxHmshV8xFDKei6Q3"):
        self.apikey = apikey
        logPrint("[SAFECASTAPI] API Key = %s" % apikey)

    def setMetadata(self, title, description, credits, cities, orientation = "Facing Back", height = 1):
        self.title = title
        self.description = description
        self.credits = credits
        self.cities = cities
        self.orientation = orientation
        self.height = height

    def upload(self, filename):
        # From http://stackoverflow.com/questions/680305/using-multipartposthandler-to-post-form-data-with-python
        datagen, headers = multipart_encode({
            "bgeigie_import[source]": open(filename),
            "bgeigie_import[name]": "%s" % self.title,
            "bgeigie_import[description]": "%s" % self.description,
            "bgeigie_import[credits]": "%s" % self.credits,
            "bgeigie_import[cities]": "%s" % self.cities,
            "bgeigie_import[orientation]": "%s" % self.orientation,
            "bgeigie_import[height]": self.height,
            })

        logPrint("[SAFECASTAPI] Uploading %s [name=%s, description=%s, credits=%s]" % (filename, self.title, self.description, self.credits))

        try:
            # Create the Request object
            request = urllib2.Request("http://api.safecast.org/bgeigie_imports.json?api_key=%s" % self.apikey, datagen, headers)
            # Actually do the request, and get the response
            print urllib2.urlopen(request).read()
        except:
            logPrint("[SAFECASTAPI] Upload failed:")
            logPrint('-'*60)
            traceback.print_exc(file=sys.stdout)
            logPrint('-'*60)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    parser = OptionParser("Usage: export_safecast [options] <log-file>")
    parser.add_option("-k", "--apikey",
                      type=str, dest="apikey", default="JpwWxHmshV8xFDKei6Q3",
                      help="specify the Safecast API Key to use")
    parser.add_option("-l", "--location",
                      type=str, dest="location", default="Unknown",
                      help="specify the location")
    parser.add_option("-d", "--details",
                      type=str, dest="details", default="Unknown",
                      help="specify the details")
    parser.add_option("-c", "--credits",
                      type=str, dest="credits", default="Unknown",
                      help="specify the credits")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("Wrong number of arguments")

    api = SafecastAPI(options.apikey)
    files = glob.glob(args[0])
    for f in files:
        api.setMetadata(os.path.basename(f), options.details, options.credits, options.location)
        api.upload(f)
