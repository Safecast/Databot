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

# email modules
import smtplib
import email, getpass, imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import Encoders

# zip file support
import zipfile

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
   def fetch(self, folder):
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
     report = 0
     for emailid in items:
         logPrint("[GMAIL] Processing email id %s" % emailid)
         resp, data = m.fetch(emailid, "(RFC822)") # fetching the mail
         email_body = data[0][1] # getting the mail content
         mail = email.message_from_string(email_body)

         # Check if any attachments at all
         if mail.get_content_maintype() != 'multipart':
           continue

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

         # If no special type requested, set to default
         if not report:
           options.pdf = True
           options.kml = True

         # Default recipient is the sender
         email_pattern = re.compile("[-a-zA-Z0-9._]+@[-a-zA-Z0-9_]+.[a-zA-Z0-9_.]+")
         mailto = re.findall(email_pattern, mail["From"])

         # Check for emails in "Subject"
         emails = re.findall(email_pattern, mail["Subject"])
         if len(emails):
           mailto = emails

         # Check for emails in "To"
         emails = re.findall(email_pattern, mail["To"])
         emails = [e for e in emails if e != self.user] # except user itself
         if len(emails):
           mailto = emails

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

             if (os.path.splitext(filename)[1]).upper() != ".LOG":
                logPrint("Check for attached zip file ...")
                try:
                  filezip = zipfile.ZipFile(att_path, "r")
                  for info in filezip.infolist():
                     if (os.path.splitext(info.filename)[1]).upper() == ".LOG":
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

     logPrint("[GMAIL] Done.")
     return result

   # --------------------------------------------------------------------------
   # Send email to recipients with attachments
   # --------------------------------------------------------------------------
   def send(self, recipients, files):
     self.recipients = recipients      
     self.files = files

     for report in self.files:
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
  else:
    logPrint("Configuration file is missing")
    sys.exit(0)

  print '='*80

  # Start processing emails
  gmail = Gmail(user, password)
  result = gmail.fetch("logs")

  if (len(result)):
    mailto, filelist, options = result
    
    # Remove blacklisted recipients
    mailto = [email for email in mailto if email not in blacklist]
    
    # Create email body
    reports = processFiles(filelist, options)

    # Send emails with attachments
    if recipients != "": 
        # default recipients
        print "Default recipients =",recipients
        mailto = [m.strip() for m in recipients.split(",")]
    gmail.send(mailto, reports)

  print '='*80

