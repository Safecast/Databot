SafecastLog2Pdf
===============

Safecast tool to convert bGeigie logs to static pdf maps

![Screenshot](https://github.com/bidouilles/SafecastLog2Pdf/blob/master/samples/screenshot.jpg)

Requirements
------------

* python 2.6
* PIL
* matplotlib, basemap
* numpy
* reporlab

Usage
-----
    > bgeigie_report.py -h
    Usage: bgeigie [options] <log-file>

    Options:
      -h, --help            show this help message and exit
      -l LANGUAGE, --language=LANGUAGE
                            specify the default language (default jp)
      -p, --pdf             enable PDF report
      -k, --kml             enable KML report
      -g, --gpx             enable GPX report
      -c, --csv             enable CSV report

The tool will generate a .jpg rendering of the map, a .html summary table (ready to be attached to emails), a zipped kml file and a .pdf report file.

License
-------
The Safecast tool is released under the CC0 license. See CC0.txt for details.


