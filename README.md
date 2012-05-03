# SafecastLog2Pdf

Safecast tool to convert bGeigie logs to static pdf maps

<img src=https://github.com/bidouilles/SafecastLog2Pdf/blob/master/samples/screenshot.jpg" alt="Scheenshot" title="Scheenshot" align="center" />

## Requirements

* python 2.6
* PIL
* matplotlib, basemap
* numpy
* reporlab

## Usage

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

## Email support

The `process_email.py` script is in charge of fetching/sending reports.
In the subject line of your email, type in these tags: [en] for English mode, [pdf] for PDF report, [kml] for KML report, [gpx] for GPX report and [csv] for CSV report (default is [pdf][kml])

### Configuration
The settings for the email account are stored in `.safecast.conf` file.

    [gmail]
    user=<user-name>@gmail.com
    password=<password>

### Usage

It can be embedded in a bash script like
    #!/bin/bash
    while true; do
      /opt/safecast/process_email.py
      sleep 60
    done

or schedule with cron in a crontab like
    */5     *      *     *    *    /opt/safecast/process_mail.py

### License

The Safecast tool is released under the CC0 license. See CC0.txt for details.


