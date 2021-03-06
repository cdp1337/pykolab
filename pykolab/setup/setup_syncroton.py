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

import os
import subprocess
import sys
import time

import components

import pykolab

from pykolab import utils
from pykolab.constants import *
from pykolab.translate import _

log = pykolab.getLogger('pykolab.setup')
conf = pykolab.getConf()

def __init__():
    components.register('syncroton', execute, description=description(), after=['mysql','ldap','roundcube'])

def description():
    return _("Setup Syncroton.")

def execute(*args, **kw):
    schema_files = []
    for root, directories, filenames in os.walk('/usr/share/doc/'):
        for directory in directories:
            if directory.startswith("kolab-syncroton"):
                for root, directories, filenames in os.walk(os.path.join(root, directory)):
                    for filename in filenames:
                        if filename.startswith('mysql.initial') and filename.endswith('.sql'):
                            schema_filepath = os.path.join(root,filename)
                            if not schema_filepath in schema_files:
                                schema_files.append(schema_filepath)
                                break

                if len(schema_files) > 0:
                    break
        if len(schema_files) > 0:
            break

    if not os.path.isfile('/tmp/kolab-setup-my.cnf'):
        utils.multiline_message(
                """Please supply the MySQL root password"""
            )

        mysql_root_password = utils.ask_question(
                _("MySQL root password"),
                password=True
            )

        data = """
[mysql]
user=root
password='%s'
""" % (mysql_root_password)

        fp = open('/tmp/kolab-setup-my.cnf', 'w')
        os.chmod('/tmp/kolab-setup-my.cnf', 0600)
        fp.write(data)
        fp.close()

    for schema_file in schema_files:
        p1 = subprocess.Popen(['cat', schema_file], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['mysql', '--defaults-file=/tmp/kolab-setup-my.cnf', 'roundcube'], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()

    time.sleep(2)

    httpservice = 'httpd.service'

    if os.path.isfile('/usr/lib/systemd/system/apache2.service'):
        httpservice = 'apache2.service'

    if os.path.isdir('/lib/systemd/system/apache2.service.d'):
        httpservice = 'apache2.service'

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'restart', httpservice])
    elif os.path.isfile('/sbin/service'):
        subprocess.call(['/sbin/service', 'httpd', 'restart'])
    elif os.path.isfile('/usr/sbin/service'):
        subprocess.call(['/usr/sbin/service','apache2','restart'])
    else:
        log.error(_("Could not start the webserver server service."))

    if os.path.isfile('/bin/systemctl'):
        subprocess.call(['/bin/systemctl', 'enable', httpservice])
    elif os.path.isfile('/sbin/chkconfig'):
        subprocess.call(['/sbin/chkconfig', 'httpd', 'on'])
    elif os.path.isfile('/usr/sbin/update-rc.d'):
        subprocess.call(['/usr/sbin/update-rc.d', 'apache2', 'defaults'])
    else:
        log.error(_("Could not configure to start on boot, the " + \
                "webserver server service."))

