import time
import pykolab
import smtplib
import email
import datetime
import uuid

from pykolab import wap_client
from pykolab.auth import Auth
from pykolab.imap import IMAP
from wallace import module_resources

from icalendar import Calendar
from email import message_from_string
from twisted.trial import unittest

import tests.functional.resource_func as funcs

conf = pykolab.getConf()

itip_invitation = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
Date: Tue, 25 Feb 2014 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c1016d7@example.org>
User-Agent: Roundcube Webmail/0.9-0.3.el6.kolab_3.0
To: %s
Subject: "test" has been created

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/plain; charset=UTF-8; format=flowed
Content-Transfer-Encoding: quoted-printable

*test*

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/calendar; charset=UTF-8; method=REQUEST; name=event.ics
Content-Disposition: attachment; filename=event.ics
Content-Transfer-Encoding: 8bit

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube Webmail 0.9-0.3.el6.kolab_3.0//NONSGML Calendar//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:%s
DTSTAMP:20140213T1254140
DTSTART;TZID=Europe/London:%s
DTEND;TZID=Europe/London:%s
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:%s
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
--=_c8894dbdb8baeedacae836230e3436fd--
"""

itip_update = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
Date: Tue, 25 Feb 2014 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c1016d7@example.org>
User-Agent: Roundcube Webmail/0.9-0.3.el6.kolab_3.0
To: %s
Subject: "test" has been updated

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/plain; charset=UTF-8; format=flowed
Content-Transfer-Encoding: quoted-printable

*test* updated

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/calendar; charset=UTF-8; method=REQUEST; name=event.ics
Content-Disposition: attachment; filename=event.ics
Content-Transfer-Encoding: 8bit

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube Webmail 0.9-0.3.el6.kolab_3.0//NONSGML Calendar//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:%s
DTSTAMP:20140215T1254140
DTSTART;TZID=Europe/London:%s
DTEND;TZID=Europe/London:%s
SEQUENCE:2
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:%s
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
--=_c8894dbdb8baeedacae836230e3436fd--
"""

itip_cancellation = """Return-Path: <john.doe@example.org>
Content-Type: text/calendar; method=CANCEL; charset=UTF-8
Content-Transfer-Encoding: quoted-printable
To: %s
From: john.doe@example.org
Date: Mon, 24 Feb 2014 11:27:28 +0100
Message-ID: <1a3aa8995e83dd24cf9247e538ac91ff@example.org>
Subject: "test" cancelled

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube Webmail 0.9-0.3.el6.kolab_3.0//NONSGML Calendar//EN
CALSCALE:GREGORIAN
METHOD:CANCEL
BEGIN:VEVENT
UID:%s
DTSTAMP:20140218T1254140
DTSTART;TZID=3DEurope/London:20120713T100000
DTEND;TZID=3DEurope/London:20120713T110000
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN=3D"Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=3DREQ-PARTICIPANT;PARTSTAT=3DACCEPTED;RSVP=3DTRUE:mailt=
o:%s
TRANSP:OPAQUE
SEQUENCE:3
END:VEVENT
END:VCALENDAR
"""

class TestResourceInvitation(unittest.TestCase):

    john = None

    @classmethod
    def setUp(self):
        """ Compatibility for twisted.trial.unittest
        """
        if not self.john:
            self.setup_class()

    @classmethod
    def setup_class(self, *args, **kw):
        from tests.functional.purge_users import purge_users
        purge_users()

        self.john = {
            'displayname': 'John Doe',
            'mail': 'john.doe@example.org',
            'sender': 'John Doe <john.doe@example.org>',
            'mailbox': 'user/john.doe@example.org'
        }

        from tests.functional.user_add import user_add
        user_add("John", "Doe")

        funcs.purge_resources()
        self.audi = funcs.resource_add("car", "Audi A4")
        self.passat = funcs.resource_add("car", "VW Passat")
        self.boxter = funcs.resource_add("car", "Porsche Boxter S")
        self.cars = funcs.resource_add("collection", "Company Cars", [ self.audi['dn'], self.passat['dn'], self.boxter['dn'] ])

        time.sleep(1)
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

    def send_message(self, msg_source, to_addr, from_addr=None):
        if from_addr is None:
            from_addr = self.john['mail']

        smtp = smtplib.SMTP('localhost', 10026)
        smtp.sendmail(from_addr, to_addr, msg_source)

    def send_itip_invitation(self, resource_email, start=None):
        if start is None:
            start = datetime.datetime.now()

        uid = str(uuid.uuid4())
        end = start + datetime.timedelta(hours=4)
        self.send_message(itip_invitation % (
                resource_email,
                uid,
                start.strftime('%Y%m%dT%H%M%S'),
                end.strftime('%Y%m%dT%H%M%S'),
                resource_email
            ),
            resource_email)

        return uid

    def send_itip_update(self, resource_email, uid, start=None):
        if start is None:
            start = datetime.datetime.now()

        end = start + datetime.timedelta(hours=4)
        self.send_message(itip_update % (
                resource_email,
                uid,
                start.strftime('%Y%m%dT%H%M%S'),
                end.strftime('%Y%m%dT%H%M%S'),
                resource_email
            ),
            resource_email)

        return uid

    def send_itip_cancel(self, resource_email, uid):
        self.send_message(itip_cancellation % (
                resource_email,
                uid,
                resource_email
            ),
            resource_email)

        return uid


    def check_message_received(self, subject, from_addr=None):
        imap = IMAP()
        imap.connect()
        imap.set_acl(self.john['mailbox'], "cyrus-admin", "lrs")
        imap.imap.m.select(self.john['mailbox'])

        found = None
        retries = 10

        while not found and retries > 0:
            retries -= 1

            typ, data = imap.imap.m.search(None, '(UNDELETED HEADER FROM "%s")' % (from_addr) if from_addr else 'UNDELETED')
            for num in data[0].split():
                typ, msg = imap.imap.m.fetch(num, '(RFC822)')
                message = message_from_string(msg[0][1])
                if message['Subject'] == subject:
                    found = message
                    break

            time.sleep(1)

        imap.disconnect()

        return found

    def check_resource_calendar_event(self, mailbox, uid=None):
        imap = IMAP()
        imap.connect()

        imap.imap.m.select(u'"'+mailbox+'"')

        found = None
        retries = 10

        while not found and retries > 0:
            retries -= 1

            typ, data = imap.imap.m.search(None, '(UNDELETED HEADER SUBJECT "%s")' % (uid) if uid else '(UNDELETED HEADER X-Kolab-Type "application/x-vnd.kolab.event")')
            for num in data[0].split():
                typ, data = imap.imap.m.fetch(num, '(RFC822)')
                event_message = message_from_string(data[0][1])

                # return matching UID or first event found
                if uid and event_message['subject'] != uid:
                    continue

                for part in event_message.walk():
                    if part.get_content_type() == "application/calendar+xml":
                        payload = part.get_payload(decode=True)
                        found = pykolab.xml.event_from_string(payload)
                        break

                if found:
                    break

            time.sleep(1)

        return found

    def purge_mailbox(self, mailbox):
        imap = IMAP()
        imap.connect()
        imap.set_acl(mailbox, "cyrus-admin", "lrwcdest")
        imap.imap.m.select(u'"'+mailbox+'"')

        typ, data = imap.imap.m.search(None, 'ALL')
        for num in data[0].split():
            imap.imap.m.store(num, '+FLAGS', '\\Deleted')

        imap.imap.m.expunge()
        imap.disconnect()


    def test_001_resource_from_email_address(self):
        resource = module_resources.resource_record_from_email_address(self.audi['mail'])
        self.assertEqual(len(resource), 1)
        self.assertEqual(resource[0], self.audi['dn'])

        collection = module_resources.resource_record_from_email_address(self.cars['mail'])
        self.assertEqual(len(collection), 1)
        self.assertEqual(collection[0], self.cars['dn'])


    def test_002_invite_resource(self):
        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,7,13, 10,0,0))

        response = self.check_message_received("Meeting Request ACCEPTED", self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test")


    def test_003_invite_resource_conflict(self):
        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,7,13, 12,0,0))

        response = self.check_message_received("Meeting Request DECLINED", self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        self.assertEqual(self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid), None)


    def test_004_invite_resource_collection(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.cars['mail'], datetime.datetime(2014,7,13, 12,0,0))

        # one of the collection members accepted the reservation
        accept = self.check_message_received("Meeting Request ACCEPTED")
        self.assertIsInstance(accept, email.message.Message)
        self.assertIn(accept['from'], [ self.passat['mail'], self.boxter['mail'] ])

        # check booking in the delegatee's resource calendar
        delegatee = self.passat if accept['from'] == self.passat['mail'] else self.boxter
        self.assertIsInstance(self.check_resource_calendar_event(delegatee['kolabtargetfolder'], uid), pykolab.xml.Event)

        # resource collection respons with a DELEGATED message
        response = self.check_message_received("Meeting Request DELEGATED", self.cars['mail'])
        self.assertIsInstance(response, email.message.Message)


    def test_005_rescheduling_reservation(self):
        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,5,1, 10,0,0))

        response = self.check_message_received("Meeting Request ACCEPTED", self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        self.purge_mailbox(self.john['mailbox'])
        self.send_itip_update(self.audi['mail'], uid, datetime.datetime(2014,5,1, 12,0,0)) # conflict with myself

        response = self.check_message_received("Meeting Request ACCEPTED", self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_start().hour, 12)
        self.assertEqual(event.get_sequence(), 2)


    def test_006_cancelling_revervation(self):
        uid = self.send_itip_invitation(self.boxter['mail'], datetime.datetime(2014,5,1, 10,0,0))
        self.assertIsInstance(self.check_resource_calendar_event(self.boxter['kolabtargetfolder'], uid), pykolab.xml.Event)

        self.send_itip_cancel(self.boxter['mail'], uid)

        time.sleep(2)  # wait for IMAP to update
        self.assertEqual(self.check_resource_calendar_event(self.boxter['kolabtargetfolder'], uid), None)

        # make new reservation to the now free'd slot
        self.send_itip_invitation(self.boxter['mail'], datetime.datetime(2014,5,1, 9,0,0))

        response = self.check_message_received("Meeting Request ACCEPTED", self.boxter['mail'])
        self.assertIsInstance(response, email.message.Message)
