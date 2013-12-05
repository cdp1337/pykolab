#!/usr/bin/python
#
# Copyright 2010-2013 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import smtplib
import socket
import sys

# For development purposes
sys.path.extend(['.', '..'])

from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

def send_mail(send_from, send_to, send_with=None):
    smtp = smtplib.SMTP("localhost", 10026)
    smtp.set_debuglevel(True)
    subject = "This is a Kolab load test mail"
    text = """Hi there,

I am a Kolab Groupware test email, generated by a script that makes
me send lots of email to lots of people using one account and a bunch
of delegation blah.

Your response, though completely unnecessary, would be appreciated, because
being a fictitious character doesn't do my address book of friends any good.

Kind regards,

Lucy Meier.
"""

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach( MIMEText(text) )

    #msg.attach( MIMEBase('application', open('/boot/initrd-plymouth.img').read()) )

    smtp.sendmail(send_from, send_to, msg.as_string())

if __name__ == "__main__":
    #send_to = [
            #'Jeroen van Meeuwen <jeroen.vanmeeuwen@klab.cc>',
            #'Aleksander Machniak <aleksander.machniak@klab.cc>',
            #'Georg Greve <georg.greve@klab.cc>',
            #'Paul Adams <paul.adams@klab.cc>',
            #'Thomas Broderli <thomas.broderli@klab.cc>',
            #'Christoph Wickert <christoph.wickert@klab.cc>',
            #'Lucy Meier <lucy.meier@klab.cc>',
        #]


    #send_mail(
            #'Jeroen van Meeuwen <jeroen.vanmeeuwen@klab.cc>',
            #send_to
        #)

    #send_mail(
            #'Lucy Meier on behalf of Paul Adams <paul.adams@test90.kolabsys.com>',
            #send_to
        #)

    #send_mail(
            #'Lucy Meier on behalf of Georg Greve <georg.greve@test90.kolabsys.com>',
            #send_to
        #)

    send_to = [
            'Jeroen van Meeuwen (REJECT) <vanmeeuwen+reject@kolabsys.com>',
            'Jeroen van Meeuwen (HOLD) <vanmeeuwen+hold@kolabsys.com>',
            'Jeroen van Meeuwen (DEFER) <vanmeeuwen+defer@kolabsys.com>',
            'Jeroen van Meeuwen (ACCEPT) <vanmeeuwen+accept@kolabsys.com>',
            'Jeroen "kanarip" van Meeuwen (ACCEPT) <kanarip+accept@kolabsys.com>',
            'Jeroen "kanarip" van Meeuwen (REJECT) <kanarip+reject@kolabsys.com>',
            'Lucy Meier (REJECT) <meier+reject@kolabsys.com>',
            'Georg Greve (REJECT) <greve+reject@kolabsys.com>',
        ]

    send_mail('Jeroen van Meeuwen <vanmeeuwen@kolabsys.com>', send_to)
