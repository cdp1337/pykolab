# -*- coding: utf-8 -*-
# Copyright 2010-2012 Kolab Systems AG (http://www.kolabsys.com)
#
# Jeroen van Meeuwen (Kolab Systems) <vanmeeuwen a kolabsys.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 or, at your option, any later version
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#

import json
import os
import tempfile
import time

from email import message_from_string
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.utils import formataddr
from email.utils import getaddresses

import modules

import pykolab

from pykolab.translate import _

log = pykolab.getLogger('pykolab.wallace')
conf = pykolab.getConf()

mybasepath = '/var/spool/pykolab/wallace/footer/'

def __init__():
    modules.register('footer', execute, description=description())

def description():
    return """Append a footer to messages."""

def execute(*args, **kw):
    if not os.path.isdir(mybasepath):
        os.makedirs(mybasepath)

    for stage in ['incoming', 'ACCEPT' ]:
        if not os.path.isdir(os.path.join(mybasepath, stage)):
            os.makedirs(os.path.join(mybasepath, stage))

    # TODO: Test for correct call.
    filepath = args[0]

    if kw.has_key('stage'):
        log.debug(_("Issuing callback after processing to stage %s") % (kw['stage']), level=8)
        log.debug(_("Testing cb_action_%s()") % (kw['stage']), level=8)
        if hasattr(modules, 'cb_action_%s' % (kw['stage'])):
            log.debug(_("Attempting to execute cb_action_%s()") % (kw['stage']), level=8)
            exec('modules.cb_action_%s(%r, %r)' % (kw['stage'],'optout',filepath))
            return

    log.debug(_("Executing module footer for %r, %r") % (args, kw), level=8)

    new_filepath = os.path.join('/var/spool/pykolab/wallace/footer/incoming', os.path.basename(filepath))
    os.rename(filepath, new_filepath)
    filepath = new_filepath

    _message = json.load(open(filepath, 'r'))
    message = message_from_string("%s" % (str(_message['data'])))

    # Possible footer answers are limited to ACCEPT only
    answers = [ 'ACCEPT' ]

    footer = {}

    footer_html_file = conf.get('wallace', 'footer_html')
    footer_text_file = conf.get('wallace', 'footer_text')

    if not os.path.isfile(footer_text_file) and not os.path.isfile(footer_html_file):
        exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','footer', filepath))
        return
        
    if os.path.isfile(footer_text_file):
        footer['plain'] = open(footer_text_file, 'r').read()

    if not os.path.isfile(footer_html_file):
        footer['html'] = '<p>' + self.footer['plain'] + '</p>'
    else:
        footer['html'] = open(footer_html_file, 'r').read()
        if footer['html'] == "":
            footer['html'] = '<p>' + self.footer['plain'] + '</p>'

    if footer['plain'] == "" and footer['html'] == "<p></p>":
        exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','footer', filepath))
        return
        
    footer_added = False

    try:
        _footer_added = message.get("X-Wallace-Footer")
    except:
        pass

    if _footer_added == "YES":
        exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','footer', filepath))
        return

    if message.is_multipart():
        if message.get_content_type() == "multipart/alternative":
            log.debug("The message content type is multipart/alternative.")

        for part in message.walk():
            disposition = None

            try:
                content_type = part.get_content_type()
            except:
                continue

            try:
                disposition = part.get("Content-Disposition")
            except:
                pass

            if not disposition == None:
                continue

            if content_type == "text/plain":
                content = part.get_payload()
                content += "\n\n--\n%s" % (footer['plain'])
                part.set_payload(content)
                footer_added = True

            elif content_type == "text/html":
                content = part.get_payload()
                content += "\n<!-- footer appended by Wallace -->\n"
                content += "\n<html><body><hr />%s</body></html>\n" % (footer['html'])
                part.set_payload(content)
                footer_added = True

    else:
        # Check the main content-type.
        if message.get_content_type() == "text/html":
            content = message.get_payload()
            content += "\n<!-- footer appended by Wallace -->\n"
            content += "\n<html><body><hr />%s</body></html>\n" % (footer['html'])
            message.set_payload(content)
            footer_added = True

        else:
            content = message.get_payload()
            content += "\n\n--\n%s" % (footer['plain'])
            message.set_payload(content)
            footer_added = True

    if footer_added:
        log.debug("Footer attached.")
        message.add_header("X-Wallace-Footer", "YES")

    _message['data'] = "%s" % (str(message.as_string()))

    (fp, new_filepath) = tempfile.mkstemp(dir="/var/spool/pykolab/wallace/footer/ACCEPT")
    os.write(fp, json.dumps(_message))
    os.close(fp)
    os.unlink(filepath)

    exec('modules.cb_action_%s(%r, %r)' % ('ACCEPT','footer', new_filepath))