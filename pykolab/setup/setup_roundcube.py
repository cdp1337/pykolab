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

from Cheetah.Template import Template
import grp
import hashlib
import os
import random
import re
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
    components.register('roundcube', execute, description=description(), after=['mysql','ldap'])

def description():
    return _("Setup Roundcube.")

def execute(*args, **kw):
    print >> sys.stderr, utils.multiline_message(
            _("""
                    Please supply a password for the MySQL user 'roundcube'.
                    This password will be used by the Roundcube webmail
                    interface.
                """)
        )

    mysql_roundcube_password = utils.ask_question(
            _("MySQL roundcube password"),
            default=utils.generate_password(),
            password=True,
            confirm=True
        )

    conf.mysql_roundcube_password = mysql_roundcube_password

    rc_settings = {
            'des_key': re.sub(
                    r'[^a-zA-Z0-9]',
                    "",
                    "%s%s" % (
                            hashlib.md5("%s" % random.random()).digest().encode("base64"),
                            hashlib.md5("%s" % random.random()).digest().encode("base64")
                        )
                )[:24],

            'imap_admin_login': conf.get('cyrus-imap', 'admin_login'),
            'imap_admin_password': conf.get('cyrus-imap', 'admin_password'),
            'ldap_base_dn': conf.get('ldap', 'base_dn'),
            'ldap_group_base_dn': conf.get('ldap', 'group_base_dn'),
            'ldap_group_filter': conf.get('ldap', 'group_filter'),
            'ldap_ldap_uri': conf.get('ldap', 'ldap_uri'),
            'ldap_resource_base_dn': conf.get('ldap', 'resource_base_dn'),
            'ldap_resource_filter': conf.get('ldap', 'resource_filter'),
            'ldap_service_bind_dn': conf.get('ldap', 'service_bind_dn'),
            'ldap_service_bind_pw': conf.get('ldap', 'service_bind_pw'),
            'ldap_user_base_dn': conf.get('ldap', 'user_base_dn'),
            'ldap_user_filter': conf.get('ldap', 'user_filter'),
            'primary_domain': conf.get('kolab','primary_domain'),
            'mysql_uri': 'mysqli://roundcube:%s@localhost/roundcube' % (mysql_roundcube_password),
            'conf': conf
        }

    rc_paths = [
            "/usr/share/roundcubemail/",
            "/usr/share/roundcube/",
            "/srv/www/roundcubemail/",
            "/var/www/roundcubemail/"
        ]

    rcpath = ''
    for rc_path in rc_paths:
        if os.path.isdir(rc_path):
            rcpath = rc_path
            break

    if not os.path.isdir(rcpath):
        log.error(_("Roundcube installation path not found."))
        return

    if os.access(rcpath + 'skins/enterprise/', os.R_OK):
        rc_settings['skin'] = 'enterprise'
    elif os.access(rcpath + 'skins/chameleon/', os.R_OK):
        rc_settings['skin'] = 'chameleon'
    else:
        rc_settings['skin'] = 'larry'

    want_files = [
            'acl.inc.php',
            'calendar.inc.php',
            'config.inc.php',
            'kolab_addressbook.inc.php',
            'kolab_auth.inc.php',
            'kolab_delegation.inc.php',
            'kolab_files.inc.php',
            'kolab_folders.inc.php',
            'libkolab.inc.php',
            'managesieve.inc.php',
            'owncloud.inc.php',
            'password.inc.php',
            'recipient_to_contact.inc.php',
            'terms.html',
            'terms.inc.php'
        ]

    for want_file in want_files:
        template_file = None
        if os.path.isfile('/etc/kolab/templates/roundcubemail/%s.tpl' % (want_file)):
            template_file = '/etc/kolab/templates/roundcubemail/%s.tpl' % (want_file)
        elif os.path.isfile('/usr/share/kolab/templates/roundcubemail/%s.tpl' % (want_file)):
            template_file = '/usr/share/kolab/templates/roundcubemail/%s.tpl' % (want_file)
        elif os.path.isfile(os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'roundcubemail', '%s.tpl' % (want_file)))):
            template_file = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'share', 'templates', 'roundcubemail', '%s.tpl' % (want_file)))

        if not template_file == None:
            log.debug(_("Using template file %r") % (template_file), level=8)
            fp = open(template_file, 'r')
            template_definition = fp.read()
            fp.close()

            t = Template(template_definition, searchList=[rc_settings])
            log.debug(
                    _("Successfully compiled template %r, writing out to %r") % (template_file, want_file),
                    level=8
                )

            fp = None
            if os.path.isdir('/etc/roundcubemail'):
                fp = open('/etc/roundcubemail/%s' % (want_file), 'w')
            elif os.path.isdir('/etc/roundcube'):
                fp = open('/etc/roundcube/%s' % (want_file), 'w')

            if not fp == None:
                fp.write(t.__str__())
                fp.close()

    schema_files = []
    for root, directories, filenames in os.walk('/usr/share/doc/'):
        directories.sort()
        for directory in directories:
            if directory.startswith("roundcubemail"):
                for nested_root, nested_directories, nested_filenames in os.walk(os.path.join(root, directory)):
                    for filename in nested_filenames:
                        if filename.startswith('mysql.initial') and filename.endswith('.sql'):
                            schema_filepath = os.path.join(nested_root,filename)
                            if not schema_filepath in schema_files:
                                schema_files.append(schema_filepath)

                if len(schema_files) > 0:
                    break
        if len(schema_files) > 0:
            break

    for root, directories, filenames in os.walk(rcpath + 'plugins/calendar/drivers/kolab/'):
        for filename in filenames:
            if filename.startswith('mysql') and filename.endswith('.sql'):
                schema_filepath = os.path.join(root,filename)
                if not schema_filepath in schema_files:
                    schema_files.append(schema_filepath)

    for root, directories, filenames in os.walk(rcpath + 'plugins/libkolab/'):
        for filename in filenames:
            if filename.startswith('mysql') and filename.endswith('.sql'):
                schema_filepath = os.path.join(root,filename)
                if not schema_filepath in schema_files:
                    schema_files.append(schema_filepath)

    for root, directories, filenames in os.walk('/usr/share/doc/'):
        directories.sort()
        for directory in directories:
            if directory.startswith("chwala"):
                for nested_root, nested_directories, nested_filenames in os.walk(os.path.join(root, directory)):
                    for filename in nested_filenames:
                        if filename.startswith('mysql.initial') and filename.endswith('.sql'):
                            schema_filepath = os.path.join(nested_root,filename)
                            if not schema_filepath in schema_files:
                                schema_files.append(schema_filepath)

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

    p1 = subprocess.Popen(['echo', 'create database roundcube;'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['mysql', '--defaults-file=/tmp/kolab-setup-my.cnf'], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()

    p1 = subprocess.Popen(['echo', 'GRANT ALL PRIVILEGES ON roundcube.* TO \'roundcube\'@\'localhost\' IDENTIFIED BY \'%s\';' % (mysql_roundcube_password)], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['mysql', '--defaults-file=/tmp/kolab-setup-my.cnf'], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()

    for schema_file in schema_files:
        p1 = subprocess.Popen(['cat', schema_file], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['mysql', '--defaults-file=/tmp/kolab-setup-my.cnf', 'roundcube'], stdin=p1.stdout)
        p1.stdout.close()
        p2.communicate()

    p1 = subprocess.Popen(['echo', 'FLUSH PRIVILEGES;'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['mysql', '--defaults-file=/tmp/kolab-setup-my.cnf'], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()

    time.sleep(2)

    # Find Roundcube configuration that is not readable by the
    # webserver user/group.
    if os.path.isdir('/etc/roundcubemail/'):
        rccpath = "/etc/roundcubemail/"
    elif os.path.isdir('/etc/roundcube/'):
        rccpath = "/etc/roundcube"
    else:
        log.warning(_("Cannot find the configuration directory for roundcube."))
        rccpath = None

    root_uid = 0

    webserver_gid = None

    for webserver_group in [ 'apache', 'www-data', 'www' ]:
        try:
            (a,b,webserver_gid,c) = grp.getgrnam(webserver_group)
            break
        except Exception, errmsg:
            pass

    if webserver_gid is not None:
        if rccpath is not None:
            for root, directories, filenames in os.walk(rccpath):
                for filename in filenames:
                    try:
                        os.chown(
                                os.path.join(root, filename),
                                root_uid,
                                webserver_gid
                            )
                    except Exception, errmsg:
                        pass

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

