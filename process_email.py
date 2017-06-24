#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright (C) 2011  Lionel Bergeret
#
# ----------------------------------------------------------------
# The contents of this file are distributed under the CC0 license.
# See http://creativecommons.org/publicdomain/zero/1.0/
# ----------------------------------------------------------------

# system modules
import datetime, os, sys, traceback
import ConfigParser
import re

# safecast module
from bgeigie_report import processFiles
from export_safecast import SafecastAPI

# email modules
import smtplib
import email, getpass, imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import Encoders

# zip file support
import zipfile

# Google sheets
import gspread

# -----------------------------------------------------------------------------
# Definitions
# -----------------------------------------------------------------------------
attachment_extensions = [".LOG", ".TXT"]

# -----------------------------------------------------------------------------
# Log print
# -----------------------------------------------------------------------------
def logPrint(message):
   print datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message

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
# Gmail class for fetching and sending emails
# -----------------------------------------------------------------------------
class Gmail():
   def __init__(self, user, password):
     self.user = user
     self.pwd = password
     self.folder = ""
     self.recipients = []
     self.message = ""
     self.files = []

   # --------------------------------------------------------------------------
   # Private utility methods
   # --------------------------------------------------------------------------
   def _createMessage(self, subject):
     msg = MIMEMultipart()
     msg['Subject'] = subject
     msg['From'] = self.user
     msg['To'] = ",".join(self.recipients)
     msg.preample = 'Your mail attacment follows'
     return msg;

   def _attachHTML(self, filename):
     fp = open(filename, 'rb')
     part = MIMEText(fp.read(), 'html')
     fp.close()
     return part;

   def _attachFile(self, filename):
     fp = open(filename, 'rb')
     part = MIMEBase('application', "octet-stream")
     part.set_payload( fp.read()  )
     fp.close()
     Encoders.encode_base64(part)
     part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(filename))
     return part;

   def _sendMessage(self, msg):
     # Send the email to the SMTP server.
     smtp = smtplib.SMTP('smtp.gmail.com',587)
     smtp.ehlo()
     smtp.starttls()
     smtp.ehlo()
     smtp.login(self.user,self.pwd)
     smtp.sendmail(self.user, self.recipients, msg.as_string())
     smtp.quit()

   # --------------------------------------------------------------------------
   # Fetch unseen emails attachment
   # --------------------------------------------------------------------------
   def fetch(self, folder, blacklist, postfix = ""):
     self.folder = folder

     if not os.path.exists("%s" % (self.folder)):
       os.makedirs("%s" % (self.folder))

     # connecting to the gmail imap server
     logPrint("[GMAIL] Connecting to gmail server ...")
     m = imaplib.IMAP4_SSL("imap.gmail.com")
     m.login(self.user,self.pwd)
     m.select("[Gmail]/All Mail")

     logPrint("[GMAIL] Selecting all unseen emails ...")
     resp, items = m.search(None, '(UNSEEN)')
     # Get the mails id
     items = items[0].split()
     items = items[:1] # only one by one

     result = []
     options = Options()
     options.language = "jp"
     options.charset = "iso-2022-jp"
     options.pdf = False
     options.kml = False
     options.gpx = False
     options.csv = False
     options.world = True # set as default
     options.time = True # set as default
     options.distance = True # set as default
     options.summary = False
     options.instant = False
     options.area = False
     options.peak = False
     report = 0
     for emailid in items:
         logPrint("[GMAIL] Processing email id %s" % emailid)
         resp, data = m.fetch(emailid, "(RFC822)") # fetching the mail
         email_body = data[0][1] # getting the mail content
         mail = email.message_from_string(email_body)

         # Check if any attachments at all
         if mail.get_content_maintype() != 'multipart':
           continue

         if mail["Subject"] == None:
           mail["Subject"] = ""

         # Add extra options to subject
         mail["Subject"] += postfix

         logPrint("[GMAIL] ["+mail["From"]+"] :" + mail["Subject"])

         # Check subject for any requests
         if mail["Subject"].upper().find("[EN]") != -1:
           options.language = "en"

         if mail["Subject"].upper().find("[PDF]") != -1:
           options.pdf = True
           report += 1

         if mail["Subject"].upper().find("[KML]") != -1:
           options.kml = True
           report += 1

         if mail["Subject"].upper().find("[GPX]") != -1:
           options.gpx = True
           report += 1

         if mail["Subject"].upper().find("[CSV]") != -1:
           options.csv = True
           report += 1

         if mail["Subject"].upper().find("[UTF8]") != -1:
           options.charset = "utf8"

         if mail["Subject"].upper().find("[JIS]") != -1:
           options.charset = "shift-jis"

         if mail["Subject"].upper().find("[WORLD]") != -1:
           options.world = True

         if mail["Subject"].upper().find("[SUMMARY]") != -1:
           options.summary = True

         if mail["Subject"].upper().find("[SPLIT]") != -1:
           options.area = True

         if mail["Subject"].upper().find("[PEAK60]") != -1:
           options.instant = False
           options.peak = True

         if mail["Subject"].upper().find("[PEAK5]") != -1:
           options.instant = True
           options.peak = True

         # If no special type requested, set to default
         if not report:
           options.pdf = True
           options.kml = True

         # Default recipient is the sender
         email_pattern = re.compile("[-a-zA-Z0-9._]+@[-a-zA-Z0-9_]+.[a-zA-Z0-9_.]+")
         mailto = re.findall(email_pattern, mail["From"])

         # Check for emails in "Subject"
         emails = re.findall(email_pattern, mail["Subject"])
         emails = [e for e in emails if e not in blacklist] # except if blacklisted
         if len(emails):
           mailto = emails

         # Check for emails in "To"
         emails = re.findall(email_pattern, mail["To"])
         emails = [e for e in emails if e != self.user] # except user itself
         emails = [e for e in emails if e not in blacklist] # except if blacklisted
         if len(emails):
           mailto = emails

         # Check for emails in "Cc"
         if mail["Cc"] != None:
           emails = re.findall(email_pattern, mail["Cc"])
           emails = [e for e in emails if e != self.user] # except user itself
           emails = [e for e in emails if e not in blacklist] # except if blacklisted
           if len(emails):
             mailto += emails

         # Cleanup for any duplicates
         mailto = list(set(mailto))

         # Mark as read
         m.uid('STORE', emailid, '+FLAGS', '(\Seen)')

         # Process the parts
         filelist = []
         for part in mail.walk():
             # multipart are just containers, so we skip them
             if part.get_content_maintype() == 'multipart':
                 continue

             # is this part an attachment ?
             if part.get('Content-Disposition') is None:
                 continue

             filename = part.get_filename()
             counter = 1

             # if there is no filename, we create one with a counter to avoid duplicates
             if not filename:
                 filename = 'part-%03d%s' % (counter, '.LOG')
                 counter += 1

             logPrint("[GMAIL]  - Fetching %s" % filename)
             att_path = os.path.join(self.folder, filename)

             # Write the attachment
             fp = open(att_path, 'wb')
             fp.write(part.get_payload(decode=True))
             fp.close()

             if (os.path.splitext(filename)[1]).upper() not in attachment_extensions:
                logPrint("Check for attached zip file ...")
                try:
                  filezip = zipfile.ZipFile(att_path, "r")
                  for info in filezip.infolist():
                     if (os.path.splitext(info.filename)[1]).upper() in attachment_extensions:
                       logname = os.path.join(self.folder, os.path.basename(info.filename))
                       logPrint(" - %s [%d bytes]" % (logname, info.file_size))
                       fp = open(logname, "wb")
                       data = filezip.read(info.filename)
                       fp.write(data)
                       fp.close()
                       filelist.append(logname)
                except:
                  # Wrong file, continue to next attachment
                  continue
                finally:
                  os.remove(att_path)
                logPrint("Done.")
             else:
                filelist.append(att_path)

         result = [mailto, filelist, options]

         # Upload to Safecast API
         if mail["Subject"].upper().find("[API ") != -1:
           pattern = re.compile("([a-zA-Z0-9]+)")
           position = mail["Subject"].upper().find("[API ") + 5
           apikey = re.findall(pattern, mail["Subject"][position:])[0]

           api = SafecastAPI(apikey)
           for f in filelist:
              api.setMetadata(os.path.basename(f), "", re.findall(email_pattern, mail["From"])[0], "")
              api.upload(f)

     logPrint("[GMAIL] Done.")
     return result

   # --------------------------------------------------------------------------
   # Send email to recipients with attachments
   # --------------------------------------------------------------------------
   def send(self, recipients, files):
     self.recipients = recipients
     self.files = files

     filenames = self.files.keys()
     filenames.sort()
     for report in filenames:
       try:
         summary = self.files[report]["message"]
         # Multipart emails
         msg = self._createMessage(
             'SAFECAST Radiation Survey Summary Map (%s)' % os.path.basename(report))

         logPrint("[GMAIL] "+msg['Subject'])

         # Add html email message
         html = self._attachHTML(summary)
         msg.attach(html)

         # Add report attachments
         for f in self.files[report]["attachments"]:
            logPrint("[GMAIL] - "+f)
            report = self._attachFile(f)
            msg.attach(report)

         # Send the email via our own SMTP server.
         logPrint("[GMAIL] Sending the email %s ..." % recipients)
         self._sendMessage(msg)
         logPrint("[GMAIL] Done.")

       except:
         # Generic trap if something crashed
         logPrint('-'*60)
         traceback.print_exc(file=sys.stdout)
         logPrint('-'*60)
         continue

# -----------------------------------------------------------------------------
# Google Doc class for fetching configuration
# -----------------------------------------------------------------------------
class GoogleConfig():
  def __init__(self, user, password, dockey, sheetname):
    self.dockey = dockey
    self.user = user
    self.password = password
    self.dockey = dockey
    self.sheetname = sheetname

  def fetch(self):
    logPrint("[GDOCS] Spreatsheet login [%s]" % self.user)
    gc = gspread.login(self.user, self.password)
    sht = gc.open_by_key(self.dockey)
    worksheet = sht.worksheet(self.sheetname)
    logPrint("[GDOCS] Retrieving data")
    data = worksheet.get_all_values()

    fields = data[0]
    for row in data[-1:]:
      # Zip together the field names and values
      items = zip(fields, row)

      # Add the value to our dictionary
      item = {}
      for (name, value) in items:
         item[name] = value.strip()

      logPrint("[GDOCS] %s" % item)
      return item


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == '__main__':
  # Load settings from config file
  config = ConfigParser.ConfigParser()
  config.read(os.path.realpath(os.path.dirname(sys.argv[0]))+"/.safecast.conf")

  if "gmail" in config.sections():
    user = config.get('gmail', 'user')
    password = config.get('gmail', 'password')
    recipients = config.get('gmail', 'recipients')
    blacklist = config.get('gmail', 'blacklist')
    dockey = config.get('gmail', 'dockey')
    sheetname = config.get('gmail', 'sheetname')
  else:
    logPrint("Configuration file is missing")
    sys.exit(0)

  print '='*80
  sheet = GoogleConfig(user, password, dockey, sheetname)
  # gconfig = sheet.fetch()
  # recipients += gconfig["recipients"]
  # blacklist += gconfig["blacklist"]
  print '='*80

  # Start processing emails
  gmail = Gmail(user, password)
  result = gmail.fetch("logs", blacklist, "[kml] [pdf]")

  if (len(result)):
    mailto, filelist, options = result

    # Upload logs to api.safecast.org
    #if gconfig["apikey"] != "":
    #  api = SafecastAPI(gconfig["apikey"])
    #  for f in filelist:
    #      api.setMetadata(os.path.basename(f), gconfig["details"], gconfig["credits"], gconfig["cities"])
    #      api.upload(f)

    # Create email body
    reports = processFiles(filelist, options)

    # Send emails with attachments
    if recipients != "":
        # default recipients
        print "Default recipients =",recipients
        mailto = mailto + [m.strip() for m in recipients.split(",")]
        # Cleanup for any duplicates
        mailto = list(set(mailto))

    gmail.send(mailto, reports)

  print '='*80

