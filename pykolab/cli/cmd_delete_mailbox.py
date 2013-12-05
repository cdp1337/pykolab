# -*- coding: utf-8 -*-
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

import sys

import commands

import pykolab

from pykolab.imap import IMAP
from pykolab.translate import _

log = pykolab.getLogger('pykolab.cli')
conf = pykolab.getConf()

def __init__():
    commands.register('delete_mailbox', execute, description=description(), aliases=['dm'])

def description():
    return """Delete a mailbox or sub-folder. Note that the mailbox or folder is removed recursively."""

def execute(*args, **kw):
    """
        Delete mailbox
    """

    try:
        delete_folder = conf.cli_args.pop(0)
    except IndexError, e:
        print >> sys.stderr, _("No mailbox specified")
        sys.exit(1)

    imap = IMAP()

    imap.connect()

    delete_folders = imap.list_folders(delete_folder)

    if len(delete_folders) == 0:
        print >> sys.stderr, _("No such folder(s)")
        sys.exit(1)

    for delete_folder in delete_folders:
        imap.delete_mailfolder(delete_folder)

