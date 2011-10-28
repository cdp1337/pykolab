# Copyright 2010-2011 Kolab Systems AG (http://www.kolabsys.com)
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

import logging
import os
import time

import pykolab

from pykolab.translate import _

conf = pykolab.getConf()
log = pykolab.getLogger('pykolab.auth')

class Auth(object):
    """
        This is the Authentication and Authorization module for PyKolab.
    """

    def __init__(self):
        """
            Initialize the authentication class.

            self._auth is the placeholder for domain-specific authentication
            backends. The keys are the primary domain names for each domain.
        """
        self._auth = None

        # Placeholder mapping back to the primary domain name space
        self.secondary_domains = {}

    def authenticate(self, login):
        """
            Verify login credentials supplied in login against the appropriate
            authentication backend.

            Login is a simple list of username, password, service and,
            optionally, the realm.
        """

        if len(login) == 3:
            # The realm has not been specified. See if we know whether or not
            # to use virtual_domains, as this may be a cause for the realm not
            # having been specified seperately.
            use_virtual_domains = conf.get('imap', 'virtual_domains')
            if use_virtual_domains == "userid":
                print "# Derive domain from login[0]"
            elif not use_virtual_domains:
                print "# Explicitly do not user virtual domains??"
            else:
                # Do use virtual domains, derive domain from login[0]
                print "# Derive domain from login[0]"

        if len(login[0].split('@')) > 1:
            domain = login[0].split('@')[1]
        else:
            domain = conf.get("kolab", "primary_domain")

        # realm overrides domain
        if len(login) == 4:
            domain = login[3]

        self.connect(domain)

        retval = self._auth._authenticate(login, domain)

        return retval

    def connect(self, domain=None):
        """
            Connect to the domain authentication backend using domain, or fall
            back to the primary domain specified by the configuration.
        """

        if not self._auth == None:
            return

        if domain == None:
            section = 'kolab'
            domain = conf.get('kolab', 'primary_domain')
        else:
            self.list_domains()
            section = domain

        if self.secondary_domains.has_key(domain):
            section = self.secondary_domains[domain]
            domain = self.secondary_domains[domain]

        log.debug(
                _("Connecting to Authentication backend for domain %s") %(
                        domain
                    ),
                level=8
            )

        if not conf.has_section(section):
            section = 'kolab'

        if not conf.has_option(section, 'auth_mechanism'):
            section = 'kolab'

        if conf.get(section, 'auth_mechanism') == 'ldap':
            from pykolab.auth import ldap
            self._auth = ldap.LDAP()
        elif conf.get(section, 'auth_mechanism') == 'sql':
            from pykolab.auth import sql
            self._auth = sql.SQL()

        else:
            from pykolab.auth import ldap
            self._auth = ldap.LDAP()

    def disconnect(self, domain=None):
        """
            Connect to the domain authentication backend using domain, or fall
            back to the primary domain specified by the configuration.
        """

        if domain == None:
            section = 'kolab'
            domain = conf.get('kolab', 'primary_domain')
        else:
            section = domain

        if not self._auth.has_key(section) or self._auth == None:
            return

        self._auth._disconnect()

    def find_user(self, attr, value, domain=None, **kw):
        self.connect(domain)

        if self.secondary_domains.has_key(domain):
            log.debug(
                    _("Using primary domain %s instead of secondary domain %s")
                    %(
                            self.secondary_domains[domain],
                            domain
                        ),
                    level=9
                )

            domain = self.secondary_domains[domain]

        return self._auth._find_user(attr, value, domain=domain, **kw)

    def list_domains(self):
        """
            List the domains using the auth_mechanism setting in the kolab
            section of the configuration file, either ldap or sql or (...).

            The actual setting would be used by self.connect(), and stuffed
            into self._auth, for use with self._auth._list_domains()

            For each domain found, returns a two-part tuple of the primary
            domain and a list of secondary domains (aliases).
        """

        # Connect to the global namespace
        self.connect()

        # Find the domains in the authentication backend.
        kolab_primary_domain = conf.get('kolab', 'primary_domain')

        domains = self._auth._list_domains()

        # If no domains are found, the primary domain is used.
        if len(domains) < 1:
            domains = [(kolab_primary_domain, [])]
        else:
            for primary, secondaries in domains:
                for secondary in secondaries:
                    self.secondary_domains[secondary] = primary

        return domains

    def list_users(self, primary_domain, secondary_domains=[], callback=None):
        self.connect(domain=primary_domain)
        users = self._auth._list_users(
                primary_domain,
                secondary_domains,
                callback
            )
        self.disconnect(domain=primary_domain)
        return users

    def synchronize(self, primary_domain, secondary_domains=[]):
        self.connect(domain=primary_domain)
        self.list_users(
                primary_domain,
                secondary_domains,
                callback=self._auth.sync_user
            )

    def domain_default_quota(self, domain):
        self.connect(domain=domain)

        if self.secondary_domains.has_key(domain):
            domain = self.secondary_domains[domain]

        return self._auth._domain_default_quota(domain)

    def domain_section(self, domain):
        self.connect(domain=domain)

        if self.secondary_domains.has_key(domain):
            domain = self.secondary_domains[domain]

        return self._auth._domain_section(domain)

    def get_user_attribute(self, domain, user, attribute):
        self.connect(domain=domain)

        if self.secondary_domains.has_key(domain):
            domain = self.secondary_domains[domain]

        return self._auth._get_user_attribute(user, attribute)

    def get_user_attributes(self, domain, user, attributes):
        self.connect(domain=domain)

        if self.secondary_domains.has_key(domain):
            domain = self.secondary_domains[domain]

        return self._auth._get_user_attributes(user, attributes)

    def search_mail_address(self, domain, mail_address):
        self.connect(domain=domain)

        if self.secondary_domains.has_key(domain):
            domain = self.secondary_domains[domain]

        return self._auth._search_mail_address(domain, mail_address)

    def set_user_attribute(self, domain, user, attribute, value):
        self.connect(domain=domain)

        if self.secondary_domains.has_key(domain):
            domain = self.secondary_domains[domain]

        self._auth._set_user_attribute(user, attribute, value)
