#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright (C) 2011  Lionel Bergeret
#
# ----------------------------------------------------------------
# The contents of this file are distributed under the CC0 license.
# See http://creativecommons.org/publicdomain/zero/1.0/
# ----------------------------------------------------------------

# system libraries
import os, sys, time, traceback
from datetime import datetime, timedelta
from optparse import OptionParser
import glob
import tempfile

# for py2exe binary
#os.environ['BASEMAPDATA'] = os.path.realpath(os.path.dirname(sys.argv[0]))+"/mpl_toolkits/basemap/data"

# matplotlib libraries
import matplotlib
matplotlib.use('Agg') # for CGI/cron script (no display)
import matplotlib.pyplot as plt
from matplotlib import colors
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.basemap import Basemap as Basemap

# mathematical libraries
import numpy as np
import pylab as pl
import math

# Math
from math import radians,asin,sqrt,pi,cos,sin,log,exp,atan
DEG_TO_RAD = pi/180
RAD_TO_DEG = 180/pi

# Tiles support
from PIL import Image, ImageDraw
import urllib

# Reportlab
import time
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus import Image as ImageRL
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors as colorsRL

# for py2exe (doesn't support dynamic import)
from reportlab.pdfbase import _fontdata_enc_winansi
from reportlab.pdfbase import _fontdata_enc_macroman
from reportlab.pdfbase import _fontdata_enc_standard
from reportlab.pdfbase import _fontdata_enc_symbol
from reportlab.pdfbase import _fontdata_enc_zapfdingbats
from reportlab.pdfbase import _fontdata_enc_pdfdoc
from reportlab.pdfbase import _fontdata_enc_macexpert
from reportlab.pdfbase import _fontdata_widths_courier
from reportlab.pdfbase import _fontdata_widths_courierbold
from reportlab.pdfbase import _fontdata_widths_courieroblique
from reportlab.pdfbase import _fontdata_widths_courierboldoblique
from reportlab.pdfbase import _fontdata_widths_helvetica
from reportlab.pdfbase import _fontdata_widths_helveticabold
from reportlab.pdfbase import _fontdata_widths_helveticaoblique
from reportlab.pdfbase import _fontdata_widths_helveticaboldoblique
from reportlab.pdfbase import _fontdata_widths_timesroman
from reportlab.pdfbase import _fontdata_widths_timesbold
from reportlab.pdfbase import _fontdata_widths_timesitalic
from reportlab.pdfbase import _fontdata_widths_timesbolditalic
from reportlab.pdfbase import _fontdata_widths_symbol
from reportlab.pdfbase import _fontdata_widths_zapfdingbats 

# Default parameters
dataFolder = os.path.realpath(os.path.dirname(sys.argv[0]))+"/data"
binSize = 0.1 # 0.1 km
borderSize = 1.0 # x binSize
CPMfactor = 300.0
maxDelayBetweenReadings = 2*60*60 # 2 hour is suspect (split)
maxDistanceBetweenReadings = 100*binSize # 10 km is suspect
debugMode = False

# Globals
global logfile
global pageWidth
global pageHeight

# Japan limits
JP_lat_min = 32.0
JP_lon_min = 130.0
JP_lat_max = 46.00
JP_lon_max = 147.45
JP_alt_max = 3776 # Fuji-san

# Statistic table labels
# note: http://docs.python.org/library/gettext.html could be used too
sLabels = {
  "points" : {"en": "Number of points", "jp": u"計測地点数"},
  "start"  : {"en": "Start time", "jp": u"測定開始時刻"},
  "stop"  : {"en": "Finish time", "jp": u"測定終了時刻"},
  "covered"  : {"en": "Covered area", "jp": u"測定地域"},
  "north"  : {"en": "Northernmost latitude", "jp": u"最北緯度"},
  "south"  : {"en": "Southernmost latitude", "jp": u"最南緯度"},
  "west"  : {"en": "Westernmost longitude", "jp": u"最西経度"},
  "east"  : {"en": "Easternmost longitude", "jp": u"最東経度"},
  "rmax"  : {"en": u"Maximum reading (μSv/h)", "jp": u"最高測定値（μSv/ h）"},
  "ravg"  : {"en": u"Average reading (μSv/h)", "jp": u"平均測定値（μSv/ h）"},
  "rmin"  : {"en": u"Minimum reading (μSv/h)", "jp": u"最低測定値（μSv/ h）"},
  "amax"  : {"en": "Highest altitude (m)", "jp": u"最高高度（m）"},
  "aavg"  : {"en": "Average altitude (m)", "jp": u"平均高度（m）"},
  "amin"  : {"en": "Lowest altitude (m)", "jp": u"最低高度（m）"},
  "summary"  : {"en": "Summary table", "jp": u"要約表"},
  "error"  : {"en": "Exceptions", "jp": u"例外"},
  "skipped"  : {"en": "Lines skipped from the log", "jp": u"無効なデータ列"},
  "legend"  : {"en": "The readings are averaged over 100m x 100m squares", "jp": u"測定値は平均100m四方"},
  "question" : {"en": "In case of any question or trouble, please contact <a href='mailto:data@safecast.org'>data@safecast.org</a>", "jp": u"何らかの質問あるいは問題の場合には、<a href='mailto:data@safecast.org'>data@safecast.org</a>と連絡をとってください。"},
}

# Map scale table: area size in km -> (OSM zoom level, font size, label length, dpi)
scaleTable = { 
   0.0 : {"zoom" : 16, "font": 7, "label": 4, "dpi": 100}, # from 0 to 3 km
   3.0 : {"zoom" : 15, "font": 4, "label": 4, "dpi": 150}, # from 3 to 5 km
   5.0 : {"zoom" : 15, "font": 3, "label": 3, "dpi": 200}, # from 5 to 8 km
   8.0 : {"zoom" : 13, "font": 2, "label": 3, "dpi": 250}, # from 8 to 25 km
   25.0 : {"zoom" : 11, "font": 2, "label": 1, "dpi": 300}, # from 25 to 100 km
   50.0 : {"zoom" : 10, "font": 1, "label": 0, "dpi": 300}, # over 100 km
}

# -----------------------------------------------------------------------------
# Log print
# -----------------------------------------------------------------------------
def logPrint(message):
   print datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message
# -----------------------------------------------------------------------------
# Debug decorator
# -----------------------------------------------------------------------------
def trace( debug ):
    def concreteDescriptor( aFunc ):
       if debug:
         def loggedFunc( *args, **kw ):
           logPrint("> "+ aFunc.__name__)
           try:
               result= aFunc( *args, **kw )
           except Exception, e:
               print "exception", aFunc.__name__, e
               raise
           logPrint("< "+ aFunc.__name__)
           return result
         loggedFunc.__name__= aFunc.__name__
         loggedFunc.__doc__= aFunc.__doc__
         return loggedFunc
       else:
         return aFunc
    return concreteDescriptor
# -----------------------------------------------------------------------------
# Compute distance between two geographic positions
# -----------------------------------------------------------------------------
# from http://www.johndcook.com/python_longitude_latitude.html
def distance_on_unit_sphere(lat1, long1, lat2, long2):
  try:
    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0
        
    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
        
    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians
        
    # Compute spherical distance from spherical coordinates.
        
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = 
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
    
    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
           math.cos(phi1)*math.cos(phi2))
    arc = math.acos( cos )

    # Remember to multiply arc by the radius of the earth 
    # in your favorite set of units to get length.
    return arc * 6373 # 6373 for km
  except:
    return 0


# -----------------------------------------------------------------------------
# Compute minutes difference between two datetime
# -----------------------------------------------------------------------------
def minutes_difference(stamp1, stamp2):
    delta = stamp1 - stamp2
    return 24*60*delta.days + delta.seconds/60

# -----------------------------------------------------------------------------
# Compute seconds difference between two datetime
# -----------------------------------------------------------------------------
def seconds_difference(stamp1, stamp2):
    delta = stamp1 - stamp2
    return 24*60*60*delta.days + delta.seconds

# -----------------------------------------------------------------------------
# Split bGeigie raw log file
# TODO: to be merged to loadLogFile
# -----------------------------------------------------------------------------
@trace(debugMode)
def splitLogFile(filename, timeSplit, distanceSplit):
  # Load the bGeigie log file
  bg = open(filename, "r")
  lines = bg.readlines()
  bg.close()

  # Initialize log counter
  logCounter = 1
  dlasttime = 0
  blastlat = 0
  blastlon = 0
  logBaseName = os.path.splitext(filename)[0]
  newFilename = "%s_%03d.LOG" % (logBaseName,logCounter)
  newFiles = []

  # Overwrite first file
  split = open(filename,"w")

  # Process the log
  for line in lines:
    if line[0] == "#": # ignore comments
       split.write("%s" % line)
       continue
    data = line.split(",")

    # Check for bGeigieMini or bGeigie
    if data[0] == "$BMRDD" or data[0] == "$BGRDD":
      if len(data) != 15 or data[6] != "A":
         split.write("%s" % line)
         continue

      # Unpack the data
      (s_header,s_id,s_time,
       s_cpm,s_cp5s,s_totc,
       s_rnStatus,s_latitude,s_northsouthindicator,s_longitude,s_eastwestindicator,
       s_altitude,s_gpsStatus,s_dop,s_quality) = data
    else:
      # Ignore invalid data
      split.write("%s" % line)
      continue

    # Extract date and CPM measurements
    try:
      bdate = s_time
      dtime = datetime.strptime(bdate, '%Y-%m-%dT%H:%M:%SZ')

      # Check time difference between readings
      if dlasttime != 0 and timeSplit:
         delta = seconds_difference(dtime, dlasttime)
         if delta > maxDelayBetweenReadings or delta < -maxDelayBetweenReadings:
           split.close()
           logCounter+=1
           newFilename = "%s_%03d.LOG" % (logBaseName,logCounter)
           newFiles.append(newFilename)
           split = open(newFilename,"w")
           blastlat = 0
           blastlon = 0
      dlasttime = dtime

      # Convert from GPS format (DDDMM.MMMM..) to decimal degrees    
      blat = float(s_latitude)/100
      blon = float(s_longitude)/100 
      blon = ((blon-int(blon))/60)*100+int(blon)
      blat = ((blat-int(blat))/60)*100+int(blat)
      # Outside Japan, skip the reading
      if (blat < JP_lat_min) or (blat > JP_lat_max) or (blon < JP_lon_min) or (blon > JP_lon_max):
          skippedLines["O"].append(lineCounter)
          split.write("%s" % line)
          continue
      # Too far away, split the reading
      if (blastlon != 0) and (blastlat != 0) and distanceSplit:
         deltakm = distance_on_unit_sphere(blastlat, blastlon, blat, blon)
         if deltakm > maxDistanceBetweenReadings:
           split.close()
           logCounter+=1
           newFilename = "%s_%03d.LOG" % (logBaseName,logCounter)
           newFiles.append(newFilename)
           split = open(newFilename,"w")
           dlasttime = 0
      blastlat = blat
      blastlon = blon

      split.write("%s" % line)
    except:
      # Something wrong, skip the reading
      split.write("%s" % line)
      continue 

  split.close()

  print "%d drives found in log %s" % (logCounter, filename)
  return newFiles

# -----------------------------------------------------------------------------
# Load bGeigie raw log file
# -----------------------------------------------------------------------------
@trace(debugMode)
def loadLogFile(filename, enableuSv):
  # bGeigie Log format
  # header + id + time + cpm + cp5s + totc + rnStatus + latitude + northsouthindicator + longitude + eastwestindicator + altitude + gpsStatus + dop + quality

  resultDate = []
  resultReading = []
  resultLat = []
  resultLon = []
  resultAltitude = []
  totalDose = 0

  # Load the bGeigie log file
  bg = open(filename, "r")
  lines = bg.readlines()
  bg.close()

  # Process the log
  lineCounter = 0
  dlasttime = 0
  blastlon = 0
  blastlat = 0
  blastalt = 0
  
  skippedLines = {"U": [], "T": [], "D": [], "O": []}
  # U Unknown
  # T Time issue
  # D Distance issue
  # O Out of Japan
  
  for line in lines:
    lineCounter += 1
    if line[0] == "#": continue # ignore comments
    data = line.split(",")

    # Check for bGeigieMini or bGeigie
    if data[0] == "$BMRDD" or data[0] == "$BGRDD":
      if len(data) != 15 or data[6] != "A":
         skippedLines["U"].append(lineCounter)
         continue

      # Unpack the data
      (s_header,s_id,s_time,
       s_cpm,s_cp5s,s_totc,
       s_rnStatus,s_latitude,s_northsouthindicator,s_longitude,s_eastwestindicator,
       s_altitude,s_gpsStatus,s_dop,s_quality) = data
    else:
      # Ignore invalid data
      skippedLines["U"].append(lineCounter)
      continue

    # Extract date and CPM measurements
    try:
      bdate = s_time
      dtime = datetime.strptime(bdate, '%Y-%m-%dT%H:%M:%SZ')

      # Check time difference between readings
      if dlasttime != 0:
         delta = seconds_difference(dtime, dlasttime)
         if delta > maxDelayBetweenReadings or delta < -maxDelayBetweenReadings:
           print "WARNING: line %d unexpected delay between measures [%d]" % (lineCounter, delta)
           skippedLines["T"].append(lineCounter)
           continue  
      dlasttime = dtime

      bcpm = float(s_cpm)
      if enableuSv: bcpm /= CPMfactor
      totalDose += float(s_cp5s)
      baltitude = float(s_altitude)   

      # Convert from GPS format (DDDMM.MMMM..) to decimal degrees    
      blat = float(s_latitude)/100
      blon = float(s_longitude)/100 
      blon = ((blon-int(blon))/60)*100+int(blon)
      blat = ((blat-int(blat))/60)*100+int(blat)
      # Outside Japan, skip the reading
      if (blat < JP_lat_min) or (blat > JP_lat_max) or (blon < JP_lon_min) or (blon > JP_lon_max):
          skippedLines["O"].append(lineCounter)
          continue
      # Too far away, skip the reading
      if (blastlon != 0) and (blastlat != 0):
         deltakm = distance_on_unit_sphere(blastlat, blastlon, blat, blon)
         if deltakm > maxDistanceBetweenReadings:
            skippedLines["D"].append(lineCounter)
            continue
      blastlat = blat
      blastlon = blon
          
    except:
      print '-'*60
      print "Error in line %d" % lineCounter
      print line
      traceback.print_exc(file=sys.stdout)
      print '-'*60
      # Something wrong, skip the reading
      skippedLines["U"].append(lineCounter)
      continue 

    # Store the results
    resultDate.append(bdate)
    resultReading.append(bcpm)
    resultLat.append(blat)
    resultLon.append(blon)
    # Check if altitude is valid
    if (baltitude > 0) and (baltitude < JP_alt_max):
      resultAltitude.append(baltitude)

  resultLat = np.array(resultLat)
  resultLon = np.array(resultLon)
  resultReading = np.array(resultReading)
  resultAltitude = np.array(resultAltitude)
  if enableuSv: totalDose /= CPMfactor

  print "[LOG] Lines skipped =",skippedLines

  return (resultDate, resultLat, resultLon, resultReading, resultAltitude, totalDose, skippedLines)

# -----------------------------------------------------------------------------
# Compute a rectangular binning from input data (x,y,value)
# -----------------------------------------------------------------------------
# Based on threads
# from http://stackoverflow.com/questions/2275924/how-to-get-data-in-a-histogram-bin  
#      http://stackoverflow.com/questions/8805601/efficiently-create-2d-histograms-from-large-datasets
@trace(debugMode)
def rectangularBinNumpy(x_min,y_min,x_max,y_max, data, xbins,ybins=None):
    if (ybins == None): ybins = xbins
    xdata, ydata, cpm = zip(*data)

    # Get min, max and width of dataset
    xwidth = max(1, x_max-x_min)
    ywidth = max(1, y_max-y_min)
    xSize = float(xwidth/xbins)
    ySize = float(ywidth/ybins)
    
    # Bins
    binsLon = np.array([int(x_min+x*xSize) for x in range( int(xwidth/xSize)+1)])
    dLon = np.digitize(xdata, binsLon) 
    binsLat = np.array([int(y_min+y*ySize) for y in range( int(ywidth/ySize)+1)])
    dLat = np.digitize(ydata, binsLat) 
    
    def centerbin(x,y):
     # Compute bin center position for labels
     cx = int(x*xSize+xSize/2)
     cy = int(y*ySize+ySize/2)
     return (cx,cy)

    # Initialize dictionaries
    hist = [[0.0 for x in xrange(xbins)] for y in xrange(ybins)]
    mask = [[1 for x in xrange(xbins)] for y in xrange(ybins)]
    avg = [[0.0 for x in xrange(xbins)] for y in xrange(ybins)]
    centers = [[centerbin(x,y) for x in xrange(xbins)] for y in xrange(ybins)]
    
    # Compute histogram
    for i in range(len(data)):
      x,y,c = data[i]
      xb = dLon[i] - 1
      yb = ybins - dLat[i]
      hist[yb][xb] += 1 # count per rectangles
      avg[yb][xb] += c  # total value per rectangles

    # Compute average and mask
    for xb in range(xbins):
      for yb in range(ybins):
        if hist[yb][xb] > 0.0:
          mask[yb][xb] = 0 # mask out
          hist[yb][xb] = (float(avg[yb][xb])/float(hist[yb][xb])) # average

    extent = (x_min,x_max,y_min,y_max)
    return hist, mask, extent, centers

# -----------------------------------------------------------------------------
# Hayakawa-san colormap
# -----------------------------------------------------------------------------
def hayakawasan_cmap(inuSv):
    levels = [44, 88, 175, 350, 700, 1400, 2800]
    if inuSv:
      levels = [0.125, 0.250, 0.5, 1.0, 2.0, 4.0, 8.0]
    cmap = colors.ListedColormap(['#e0efda', '#c8df97', '#fffa82', '#fccf4e', '#f0a02f', '#ec6828', '#db3036'])
    norm = colors.BoundaryNorm(levels, cmap.N)

    return levels, cmap, norm

# -----------------------------------------------------------------------------
# JP mockup colormap
# -----------------------------------------------------------------------------
def JPsafecast_cmap():
    levels = [0, 0.2, 0.5, 1.0, 5.0, 10.0]
    cmap = colors.ListedColormap(['#6bac5a', '#dbda6e', '#e184df', '#8883dd', '#d95755', '#303030'])
    norm = colors.BoundaryNorm(levels, cmap.N)

    return levels, cmap, norm

# -----------------------------------------------------------------------------
# Perform a google projection
# -----------------------------------------------------------------------------
# from http://svn.openstreetmap.org/applications/rendering/mapnik/generate_tiles.py
#
class GoogleProjection:
    def __init__(self,levels=18):
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        c = 256
        for d in range(0,levels):
            e = c/2;
            self.Bc.append(c/360.0)
            self.Cc.append(c/(2 * pi))
            self.zc.append((e,e))
            self.Ac.append(c)
            c *= 2

    def minmax (self,a,b,c):
        a = max(a,b)
        a = min(a,c)
        return a
                
    def fromLLtoPixel(self,ll,zoom):
         d = self.zc[zoom]
         e = round(d[0] + ll[0] * self.Bc[zoom])
         f = self.minmax(sin(DEG_TO_RAD * ll[1]),-0.9999,0.9999)
         g = round(d[1] + 0.5*log((1+f)/(1-f))*-self.Cc[zoom])
         return (e,g)
     
    def fromPixelToLL(self,px,zoom):
         e = self.zc[zoom]
         f = (px[0] - e[0])/self.Bc[zoom]
         g = (px[1] - e[1])/-self.Cc[zoom]
         h = RAD_TO_DEG * ( 2 * atan(exp(g)) - 0.5 * pi)
         return (f,h)

    def corners(self, gx0, gy0, gx1, gy1, zoom):
        # Calculate pixel positions of bottom-left & top-right
        p0 = (gx0 * 256, gy0 * 256)
        p1 = ((gx1 + 1) * 256, (gy1+1) * 256)

        # Convert to LatLong (EPSG:4326)
        l0 = self.fromPixelToLL(p0, zoom);
        l1 = self.fromPixelToLL(p1, zoom);

        return ([l0[0], l1[0]], [l0[1], l1[1]])

# -----------------------------------------------------------------------------
# Download a tile
# -----------------------------------------------------------------------------
def download(url, output):
    if (not os.path.exists(output)):
      print "Downloading tile %s" % (output)
      urllib.urlretrieve(url, output)
    else:
      print "Re-using tile %s" % (output)

# -----------------------------------------------------------------------------
# Load OSM tiles from an area
# -----------------------------------------------------------------------------
@trace(debugMode)
def loadTiles(lat_min,lon_min,lat_max,lon_max, zoom):
    projection = GoogleProjection()
    gx0 , gy0 = projection.fromLLtoPixel((lon_min, lat_max), zoom) # top right
    gx1 , gy1 = projection.fromLLtoPixel((lon_max, lat_min), zoom) # bottom left

    gx0 = int(gx0/256)
    gy0 = int(gy0/256)
    gx1 = int(gx1/256)
    gy1 = int(gy1/256)

    tilesX = gx1-gx0+1
    tilesY = gy1-gy0+1

    if not os.path.exists(dataFolder+"/tiles/%s" % zoom):
      os.makedirs(dataFolder+"/tiles/%s" % zoom)

    # Start looping
    gx = gx0
    gy = gy0
    images = []
    while (gx <= gx1):
      images_horizontal = []
      while (gy <= gy1):
        X = gx % (1 << zoom)
        filename = dataFolder+"/tiles/%s/%d-%d.png" % (zoom, gx, gy)
        pngurl = "http://a.tile.openstreetmap.org/%d/%d/%d.png" % (int(zoom), int(X), int(gy))
        download(pngurl, filename)

        image = Image.open(filename)
        image.load()
        images_horizontal.append((filename, image))

        gy += 1

      images.append(images_horizontal)
      gy = gy0
      gx += 1

    # Merge tiles
    spriteSheet = Image.new('RGB', (tilesX*256, tilesY*256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(spriteSheet)

    pasteX = 0
    for x in range(tilesX):
      pasteY = 0
      for y in range(tilesY):
        (filename, image) = images[x][y]
        spriteSheet.paste(image, (pasteX, pasteY))
        pasteY += 256
      pasteX += 256

    spriteSheet.save(os.path.join(tempfile.gettempdir(),"jp_map_tiles.png"), quality=50)

    c = projection.corners(gx0 , gy0, gx1 , gy1, zoom)
    return c

# -----------------------------------------------------------------------------
# Draw final map (tile layer + rectangular binning 100mx100m layer)
# -----------------------------------------------------------------------------
@trace(debugMode)
def drawMap(filename, language, showTitle):
    mapName = os.path.splitext(filename)[0]
    print "Generating %s.png ..." % mapName

    # Load data log
    dt, lat, lon, cpm, altitude, dose, skipped = loadLogFile(filename, True)
    if not len(dt):
      print "No valid data available."
      return []

    owidth = distance_on_unit_sphere(lat.min(),lon.min(),lat.min(),lon.max())
    oheight = distance_on_unit_sphere(lat.min(),lon.min(),lat.max(),lon.min())
    print "original area %.3f km x %.3f km" % (owidth, oheight)

    # Adjust label size and tiles zoom
    (zoom, fontsize, labelsize, dpi) = (16, 7, 4, 100)

    scales = scaleTable.keys()
    scales.sort()
    scales.reverse()
    for s in scales:
      if max(owidth,oheight) < s:
        continue
      else:
       print scaleTable[s]
       (zoom, fontsize, labelsize, dpi) = (scaleTable[s]["zoom"],scaleTable[s]["font"],scaleTable[s]["label"],scaleTable[s]["dpi"])
       break

    # Add 100m border around the measured area
    if (lat.min() == lat.max()):
      w100m = (lon.max()-lon.min())/(distance_on_unit_sphere(lat.min(),lon.min(),lat.min(),lon.max())/binSize)
      h100m = 0.0009*1.5
    elif (lon.min() == lon.max()):
      w100m = 0.0011*1.5
      h100m = (lat.max()-lat.min())/(distance_on_unit_sphere(lat.min(),lon.min(),lat.max(),lon.min())/binSize)
    else:
      w100m = (lon.max()-lon.min())/(distance_on_unit_sphere(lat.min(),lon.min(),lat.min(),lon.max())/binSize)
      h100m = (lat.max()-lat.min())/(distance_on_unit_sphere(lat.min(),lon.min(),lat.max(),lon.min())/binSize)

    lon_min = lon.min()-borderSize*w100m
    lon_max = lon.max()+borderSize*w100m
    lat_min = lat.min()-borderSize*h100m
    lat_max = lat.max()+borderSize*h100m

    # Compute gridsize   
    width = distance_on_unit_sphere(lat_min,lon_min,lat_min,lon_max)
    height = distance_on_unit_sphere(lat_min,lon_min,lat_max,lon_min)
    print "extended area %.3f km x %.3f km" % (width, height)
    #gridsize = (max(1,int(math.ceil(width/binSize)-borderSize*2)), max(1, int(math.ceil(height/binSize)-borderSize*2))) # 100m x 100m
    gridsize = (max(1,int(math.ceil(width/binSize))), max(1, int(math.ceil(height/binSize)))) # 100m x 100m

    pngUrl = "http://parent.tile.openstreetmap.org/cgi-bin/export?bbox=%.6f,%.6f,%.6f,%.6f&scale=%d&format=png" % (lon_min, lat_min, lon_max, lat_max, max(width, height)*3000)
    svgUrl = "http://parent.tile.openstreetmap.org/cgi-bin/export?bbox=%.6f,%.6f,%.6f,%.6f&scale=%d&format=svg" % (lon_min, lat_min, lon_max, lat_max, max(width, height)*6000)
    #print pngUrl
    #print svgUrl

    # Compute title and statistic informations
    dt.sort()
    startZ = datetime.strptime(dt[0], '%Y-%m-%dT%H:%M:%SZ')
    stopZ = datetime.strptime(dt[-1], '%Y-%m-%dT%H:%M:%SZ')
    start = startZ + timedelta(hours=+9) # GMT+9 from Zulu time
    stop = stopZ + timedelta(hours=+9) # GMT+9 from Zulu time
    title = "%s\n(%s -> %s)" % (filename, start.strftime("%Y/%m/%d %H:%M"), stop.strftime("%Y/%m/%d %H:%M"))
    statistics = u"area %.3f km x %.3f km | min %.3f µSv/h, max %.3f µSv/h, avg %.3f µSv/h | dose %.3f µSv" % (width, height, float(cpm.min()), float(cpm.max()), float(cpm.mean()), float(dose))

    statTable=[(sLabels["points"][language], len(cpm)),
               (sLabels["start"][language],start),
               (sLabels["stop"][language],"%s (%d minutes)" % (stop, minutes_difference(stopZ, startZ))),
               (sLabels["covered"][language], "%.3f km x %.3f km" % (width, height)),
               (sLabels["north"][language], ("%.6f" % lat_max)),
               (sLabels["south"][language], ("%.6f" % lat_min)),
               (sLabels["west"][language], ("%.6f" % lon_min)),
               (sLabels["east"][language], ("%.6f" % lon_max)),
               (sLabels["rmax"][language], ("%.3f" % cpm.max()).lstrip("0")),
               (sLabels["ravg"][language], ("%.3f" % cpm.mean()).lstrip("0")),
               (sLabels["rmin"][language], ("%.3f" % cpm.min()).lstrip("0")),
#               ("Total dose (µSv)", ("%.3f" % dose).lstrip("0")),
               (sLabels["aavg"][language], ("%.3f" % altitude.mean()).lstrip("0")),
               (sLabels["amin"][language], ("%.3f" % altitude.min()).lstrip("0")),
               (sLabels["amax"][language], ("%.3f" % altitude.max()).lstrip("0")),
    ]

    # Load tiles
    ctilesLon, ctilesLat = loadTiles(lat_min,lon_min,lat_max,lon_max, zoom)

    # Create the basemap
    m = Basemap(projection='merc', llcrnrlon=lon_min ,llcrnrlat=lat_min, urcrnrlon=lon_max ,urcrnrlat=lat_max, resolution='i')

    # Compute Hayakawa-san color map
    levels, cmap, normCPM = JPsafecast_cmap()

    # Project the measurements
    x,y = m(lon,lat)

    # Disable axis, strip unecessary
    plt.setp(plt.gca(), frame_on=False, xticks=[], yticks=[])

    if showTitle:
      plt.title(title, fontsize=10)

    # Add the OSM map
    tx,ty = m(ctilesLon,ctilesLat)
    xmin,xmax = min(tx),max(tx)
    ymin,ymax = min(ty),max(ty)
    tilesExtent = (xmin,xmax,ymin,ymax)
    tiles = Image.open(os.path.join(tempfile.gettempdir(),"jp_map_tiles.png")).transpose(Image.FLIP_TOP_BOTTOM)
    plt.imshow(tiles, extent = tilesExtent, alpha = 0.8)
   
    # Draw Safecast data on the map
    m.scatter(x, y, s=0.1, c=cpm, cmap=cmap, linewidths=0.1, alpha=0.1, facecolors='none', norm=normCPM)
    #m.scatter(x, y, s=3, c=cpm, cmap=cmap, linewidths=0.1, alpha=1, norm=normCPM, zorder = 5)

    # Draw the rectangle binning
    x_min,y_min = m(lon_min,lat_min)
    x_max,y_max = m(lon_max,lat_max)
    imdata, mask, extent, centers = rectangularBinNumpy(x_min,y_min,x_max,y_max,zip(x,y,cpm), gridsize[0], gridsize[1])
    drive100m = np.ma.array(imdata, mask=mask)
    plt.imshow(drive100m, extent = extent, interpolation = 'nearest', cmap=cmap, norm=normCPM, alpha = 0.9)

    # Show measurement labels
    for w in range(gridsize[0]):
      for h in range(gridsize[1]):
        tx, ty = centers[gridsize[1]-h-1][w]
        if mask[h][w] == 0:
          value = "%0.3f" % (imdata[h][w])
          value = value.lstrip("0")
          if len(value)>labelsize: value = value[:labelsize]
          if imdata[h][w] > 4.0:
            plt.text(tx,ty,value, fontsize=fontsize, ha='center',va='center',color='w', fontweight='bold')
          else:
            plt.text(tx,ty,value, fontsize=fontsize, ha='center',va='center',color='k', fontweight='bold')

    # Legend
    legend = sLabels["legend"][language]
    divider = make_axes_locatable(plt.gca())
    cax = divider.append_axes("bottom", size="5%", pad=0.05)
    cbar = plt.colorbar(cax=cax, orientation="hozrizontal", format=u"%0.3f~\nµSv/h")
    if showTitle:
       cbar.set_label(statistics, fontsize=8)
    for tick in cbar.ax.xaxis.get_major_ticks():
       tick.label.set_fontsize(8) 

    # Page size
    DefaultSize = plt.gcf().get_size_inches()
    MaxSize = max(DefaultSize[0], DefaultSize[1])
    plt.gcf().set_size_inches(MaxSize, MaxSize*(height/width))
    NewSize = plt.gcf().get_size_inches()

    # Save png file
    plt.savefig(mapName+".png", dpi = dpi, bbox_inches='tight')
    Image.open(mapName+".png").save(mapName+".jpg",quality=70) # create a 70% quality jpeg
    plt.clf() # clear the plot (free the memory for the other threads)
    pl.close('all')

    print "Done."

    return [NewSize, legend, statTable, skipped]

# -----------------------------------------------------------------------------
# Generate PDF report
# -----------------------------------------------------------------------------
# set print time
time = datetime.now().strftime("%Y-%m-%d %H:%Mh")

def firstPage(canvas, doc):
    canvas.saveState()
    # page header (with event information)
    canvas.setFont("Helvetica", 10)
    canvas.setFillGray(0.4)
    canvas.drawString(0.1*pageWidth, pageHeight-1*cm, "%s" % (logfile))

    # time
    canvas.setFont("Helvetica", 7)
    canvas.drawString(0.75*pageWidth, pageHeight-1*cm, ("Printed")+": %s" % time)

@trace(debugMode)
def generatePDFReport(mapName, language, size, legend, statisticTable):
    print "Generating report %s.pdf ..." % mapName
    Story=[]
    global pageWidth
    global pageHeight

    if language == "jp":
      from reportlab.pdfbase import pdfmetrics
      from reportlab.pdfbase.ttfonts import TTFont
      pdfmetrics.registerFont(TTFont('Japanese', dataFolder+"/font/kochi-gothic.ttf"))

    # Compute the page size
    pageWidth = (size[0]+1)*inch
    pageHeight = (size[1]+5)*inch
    pdfPageSize = (pageWidth, pageHeight)

    doc = SimpleDocTemplate(mapName+".pdf",pagesize=pdfPageSize,
                        rightMargin=10,leftMargin=10,
                        topMargin=10,bottomMargin=10)

    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    if language == "jp":
      styles.add(ParagraphStyle(name='Centered', alignment=TA_CENTER, fontName='Japanese'))
    else:
      styles.add(ParagraphStyle(name='Centered', alignment=TA_CENTER))

    # Add the safecast logo
    im = ImageRL(dataFolder+"/logo/safecast_horizontal.png")
    im.drawHeight = 3*inch*im.drawHeight / im.drawWidth
    im.drawWidth = 3*inch
    Story.append(im)

    # Add the jpg map
    im = ImageRL(mapName+".jpg", size[0]*inch, size[1]*inch)
    Story.append(im)

    # Add the legend
    ptext = '<font size=10>%s</font>' % legend
    Story.append(Paragraph(ptext, styles["Centered"]))
    Story.append(Spacer(1, 8))

    # Add the stat table
    Story.append(Spacer(1, 12))
    table = Table(statisticTable, colWidths=180, rowHeights=14)
    tableStyle = TableStyle(
        [('LINEABOVE', (0,0), (-1,0), 2, colorsRL.green),
         ('LINEABOVE', (0,1), (-1,-1), 0.25, colorsRL.black, None, (2,2,1)),
         ('LINEBELOW', (0,-1), (-1,-1), 2, colorsRL.green),
#         ('FONTSIZE', (0, 0), (-1, -1), 10),
        ])
    if language == "jp":
       tableStyle.add(*('FONT', (0,0), (-1,-1), 'Japanese', 10))
    table.setStyle(tableStyle)
    Story.append(table)

    # Render the pdf
    doc.build(Story, onFirstPage=firstPage)
    print "Done."

# -----------------------------------------------------------------------------
# Generate HTML report
# -----------------------------------------------------------------------------
@trace(debugMode)
def generateHTMLReport(mapName, language, statisticTable, skipped):
    htmlMessageHeader = """\
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/> 
    <style type="text/css">
     h1 {
	font: bold 18px "Trebuchet MS", Verdana, Arial, Helvetica,
	sans-serif;
     }
     
     body {
        font: 12px "Trebuchet MS", Verdana, Arial, Helvetica,
	sans-serif;
     }

     td {
	border: 1px solid #C1DAD7;
	background: #fff;
	padding: 6px 6px 6px 12px;
	font: 12px "Trebuchet MS", Verdana, Arial, Helvetica,
	sans-serif;
     }

     th {
	border: 1px solid #C1DAD7;
	background: #fff;
	padding: 6px 6px 6px 12px;
	font: bold 12px "Trebuchet MS", Verdana, Arial, Helvetica,
	sans-serif;
     }
    </style>
  </head>
  <body>

"""
    htmlMessageFooter = """
  </body>
</html>
"""

    htmlMessage = htmlMessageHeader

    htmlMessage += "<h1>%s</h1><table cellspacing='0'>" % sLabels["summary"][language]
    for e in statisticTable:
       htmlMessage += "<tr><th align='left'>%s</th><td>%s</td></tr>" % (e[0], e[1])
    htmlMessage += "</table>"

    if len(skipped):
      htmlMessage += "<h1>%s</h1>" % sLabels["error"][language]
      htmlMessage += "%s: %s" % (sLabels["skipped"][language], ", ".join(sum([[str(x)+y for x in skipped[y]] for y in skipped.keys()], [])))

    htmlMessage += "<br>%s" % (sLabels["question"][language])
    htmlMessage += htmlMessageFooter

    message = open(mapName+".html", "w")
    message.write(htmlMessage.encode("utf8"))
    message.close()
# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    parser = OptionParser("Usage: bgeigie [options] <log-file>")
    parser.add_option("-l", "--language", 
                      type=str, dest="language", default="jp",
                      help="specify the default language (default jp)")

    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        parser.error("Wrong number of arguments")

    files = glob.glob(args[0])

    # Split drives if necessary
    newFiles = []
    for f in files:     
      newFile = splitLogFile(f, True, False)
      newFiles += newFile

    # Generate map and report
    files += newFiles
    processStatus = []
    for f in files:
      global logfile
      logfile = os.path.basename(f)
      
      try:
        # Draw map
        mapInfo = drawMap(f, options.language, False)
        if len(mapInfo) == 0:
           # Wrong file, skip it
           continue
        size, legend, statisticTable, skipped = mapInfo
        # Generate reports
        generatePDFReport(os.path.splitext(f)[0], options.language, size, legend, statisticTable)
        generateHTMLReport(os.path.splitext(f)[0], options.language, statisticTable, skipped)
        processStatus.append((f, sum([len(skipped[e]) for e in skipped.keys()])))
      except:
        # Generic trap if something crashed
        print '-'*60
        traceback.print_exc(file=sys.stdout)
        print '-'*60
        processStatus.append((f, -1))
        continue
    
    # Display a status summary
    print '='*60
    print "Log file\tExceptions (-1 = failure)"
    for s in processStatus:
      print "%s\t%d" % s
    print '='*60
     


