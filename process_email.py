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

# safecast module
import bgeigie_report

# email modules
import smtplib
import email, getpass, imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import Encoders

# -----------------------------------------------------------------------------
# Log print
# -----------------------------------------------------------------------------
def logPrint(message):
   print datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message

# -----------------------------------------------------------------------------
# Gmail class for fetching and sending emails
# -----------------------------------------------------------------------------
class Gmail():
   def __init__(self, user, password):
     self.user = user
     self.pwd = password

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

     for emailid in items:
         logPrint("[GMAIL] Processing email id %s" % emailid)
         resp, data = m.fetch(emailid, "(RFC822)") # fetching the mail
         email_body = data[0][1] # getting the mail content
         mail = email.message_from_string(email_body)

         # Check if any attachments at all
         if mail.get_content_maintype() != 'multipart':
             continue

         logPrint("[GMAIL] ["+mail["From"]+"] :" + mail["Subject"])

         if mail["Subject"].find("[en]") != -1:
          language = "en"
         else:
          language = "jp"
         sender = mail["From"]

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
             filelist.append(att_path)

             # Check if its already there
             if not os.path.isfile(att_path) :
                 # Write the attachment
                 fp = open(att_path, 'wb')
                 fp.write(part.get_payload(decode=True))
                 fp.close()

         result = [sender, filelist, language]

     logPrint("[GMAIL] Done.")
     return result

   # --------------------------------------------------------------------------
   # Send email to recipients with attachments
   # --------------------------------------------------------------------------
   def send(self, recipients, message, files):
     self.recipients = recipients  
     self.message = message      
     self.files = files

     for f in self.files:
       try:
         # Multipart emails
         msg = MIMEMultipart()    
         msg['Subject'] = 'SAFECAST Radiation Survey Summary Map (%s)' % os.path.basename(f)
         msg['From'] = self.user
         msg['To'] = ",".join(self.recipients)
         msg.preample = 'Your mail attacment follows'

         logPrint("[GMAIL] "+msg['Subject'])

         # Add html email message
         fp = open(self.message, 'rb')
         html = MIMEText(fp.read(), 'html')
         fp.close()
         msg.attach(html)

         # Add report pdf attachment
         fp = open(f, 'rb')
         report = MIMEBase('application', "octet-stream")
         report.set_payload( fp.read()  )
         fp.close()
         Encoders.encode_base64(report)
         report.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
         msg.attach(report)

         # Send the email via our own SMTP server.
         logPrint("[GMAIL] Sending the email ...") 
         s = smtplib.SMTP('smtp.gmail.com',587)
         s.ehlo()
         s.starttls()
         s.ehlo()
         s.login(self.user,self.pwd)
         s.sendmail(self.user, self.recipients, msg.as_string())
         s.quit()

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
  else:
    logPrint("Configuration file is missing")
    sys.exit(0)

  print '='*80

  # Start processing emails
  gmail = Gmail(user, password)
  result = gmail.fetch("logs")

  if (len(result)):
    sender, filelist, language = result

    reports = []
    processStatus = []
    for f in filelist:
      bgeigie_report.logfile = os.path.basename(f)

      try:
        # Draw map
        mapInfo = bgeigie_report.drawMap(f, language, False)
        if len(mapInfo) == 0:
           # Wrong file, skip it
           continue
        size, legend, statisticTable, skipped = mapInfo
        # Generate reports
        bgeigie_report.generatePDFReport(os.path.splitext(f)[0], language, size, legend, statisticTable)
        bgeigie_report.generateHTMLReport(os.path.splitext(f)[0], language, statisticTable, skipped)
        processStatus.append((f, sum([len(skipped[e]) for e in skipped.keys()])))
      except:
        # Generic trap if something crashed
        logPrint('-'*60)
        traceback.print_exc(file=sys.stdout)
        logPrint('-'*60)
        processStatus.append((f, -1))
        continue

      reports.append(os.path.splitext(f)[0]+".pdf")

    # Display a status summary
    print '='*60
    print "Log file\tExceptions (-1 = failure)"
    for s in processStatus:
      print "%s\t%d" % s
    print '='*60

    gmail.send([sender], os.path.splitext(f)[0]+".html", reports)

  print '='*80

