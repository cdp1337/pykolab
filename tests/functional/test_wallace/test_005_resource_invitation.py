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

itip_invitation = """
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
ATTENDEE;ROLE=REQ-PARTICIPANT;CUTYPE=RESOURCE;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:%s
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""

itip_update = """
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
ATTENDEE;ROLE=REQ-PARTICIPANT;CUTYPE=RESOURCE;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:%s
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""

itip_delegated = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube//Roundcube libcalendaring 1.0-git//Sabre//Sabre VObject
  2.1.3//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:%s
DTSTAMP;VALUE=DATE-TIME:20140227T141939Z
DTSTART;VALUE=DATE-TIME;TZID=Europe/London:%s
DTEND;VALUE=DATE-TIME;TZID=Europe/London:%s
SUMMARY:test
SEQUENCE:4
ATTENDEE;CN=Company Cars;PARTSTAT=DELEGATED;ROLE=NON-PARTICIPANT;CUTYPE=IND
 IVIDUAL;RSVP=TRUE;DELEGATED-TO=resource-car-audia4@example.org:mailto:reso
 urce-collection-companycars@example.org
ATTENDEE;CN=Audi A4;PARTSTAT=ACCEPTED;ROLE=REQ-PARTICIPANT;CUTYPE=INDIVIDUA
 L;RSVP=TRUE;DELEGATED-FROM=resource-collection-companycars@example.org:mai
 lto:resource-car-audia4@example.org
ORGANIZER;CN=:mailto:john.doe@example.org
DESCRIPTION:Sent to %s
END:VEVENT
END:VCALENDAR
"""

itip_cancellation = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube Webmail 0.9-0.3.el6.kolab_3.0//NONSGML Calendar//EN
CALSCALE:GREGORIAN
METHOD:CANCEL
BEGIN:VEVENT
UID:%s
DTSTAMP:20140218T1254140
DTSTART;TZID=Europe/London:20120713T100000
DTEND;TZID=Europe/London:20120713T110000
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=TRUE:mailt=
 o:%s
TRANSP:OPAQUE
SEQUENCE:3
END:VEVENT
END:VCALENDAR
"""

itip_allday = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Roundcube Webmail 0.9-0.3.el6.kolab_3.0//NONSGML Calendar//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:%s
DTSTAMP:20140213T1254140
DTSTART;VALUE=DATE:%s
DTEND;VALUE=DATE:%s
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;CUTYPE=RESOURCE;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:%s
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""


itip_recurring = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Apple Inc.//Mac OS X 10.9.2//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:%s
DTSTAMP:20140213T1254140
DTSTART;TZID=Europe/Zurich:%s
DTEND;TZID=Europe/Zurich:%s
RRULE:FREQ=WEEKLY;INTERVAL=1;COUNT=10
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;CUTYPE=RESOURCE;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:%s
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
"""

mime_message = """MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="=_c8894dbdb8baeedacae836230e3436fd"
From: "Doe, John" <john.doe@example.org>
Date: Tue, 25 Feb 2014 13:54:14 +0100
Message-ID: <240fe7ae7e139129e9eb95213c1016d7@example.org>
User-Agent: Roundcube Webmail/0.9-0.3.el6.kolab_3.0
To: %s
Subject: "test"

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/plain; charset=UTF-8; format=flowed
Content-Transfer-Encoding: quoted-printable

*test*

--=_c8894dbdb8baeedacae836230e3436fd
Content-Type: text/calendar; charset=UTF-8; method=REQUEST; name=event.ics
Content-Disposition: attachment; filename=event.ics
Content-Transfer-Encoding: 8bit

%s
--=_c8894dbdb8baeedacae836230e3436fd--
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

    def send_message(self, itip_payload, to_addr, from_addr=None):
        if from_addr is None:
            from_addr = self.john['mail']

        smtp = smtplib.SMTP('localhost', 10026)
        smtp.sendmail(from_addr, to_addr, mime_message % (to_addr, itip_payload))

    def send_itip_invitation(self, resource_email, start=None, allday=False, template=None):
        if start is None:
            start = datetime.datetime.now()

        uid = str(uuid.uuid4())

        if allday:
            default_template = itip_allday
            end = start + datetime.timedelta(days=1)
            date_format = '%Y%m%d'
        else:
            end = start + datetime.timedelta(hours=4)
            default_template = itip_invitation
            date_format = '%Y%m%dT%H%M%S'

        self.send_message((template if template is not None else default_template) % (
                uid,
                start.strftime(date_format),
                end.strftime(date_format),
                resource_email
            ),
            resource_email)

        return uid

    def send_itip_update(self, resource_email, uid, start=None, template=None):
        if start is None:
            start = datetime.datetime.now()

        end = start + datetime.timedelta(hours=4)
        self.send_message((template if template is not None else itip_update) % (
                uid,
                start.strftime('%Y%m%dT%H%M%S'),
                end.strftime('%Y%m%dT%H%M%S'),
                resource_email
            ),
            resource_email)

        return uid

    def send_itip_cancel(self, resource_email, uid):
        self.send_message(itip_cancellation % (
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


    def find_resource_by_email(self, email):
        resource = None
        if (email.find(self.audi['mail']) >= 0):
            resource = self.audi
        if (email.find(self.passat['mail']) >= 0):
            resource = self.passat
        if (email.find(self.boxter['mail']) >= 0):
            resource = self.boxter
        return resource


    def test_001_resource_from_email_address(self):
        resource = module_resources.resource_record_from_email_address(self.audi['mail'])
        self.assertEqual(len(resource), 1)
        self.assertEqual(resource[0], self.audi['dn'])

        collection = module_resources.resource_record_from_email_address(self.cars['mail'])
        self.assertEqual(len(collection), 1)
        self.assertEqual(collection[0], self.cars['dn'])


    def test_002_invite_resource(self):
        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,7,13, 10,0,0))

        response = self.check_message_received("Reservation Request for test was ACCEPTED", self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test")


    def test_003_invite_resource_conflict(self):
        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,7,13, 12,0,0))

        response = self.check_message_received("Reservation Request for test was DECLINED", self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        self.assertEqual(self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid), None)


    def test_004_invite_resource_collection(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.cars['mail'], datetime.datetime(2014,7,13, 12,0,0))

        # one of the collection members accepted the reservation
        accept = self.check_message_received("Reservation Request for test was ACCEPTED")
        self.assertIsInstance(accept, email.message.Message)

        delegatee = self.find_resource_by_email(accept['from'])
        self.assertIn(delegatee['mail'], accept['from'])

        # check booking in the delegatee's resource calendar
        self.assertIsInstance(self.check_resource_calendar_event(delegatee['kolabtargetfolder'], uid), pykolab.xml.Event)

        # resource collection responds with a DELEGATED message
        response = self.check_message_received("Reservation Request for test was DELEGATED", self.cars['mail'])
        self.assertIsInstance(response, email.message.Message)
        self.assertIn("ROLE=NON-PARTICIPANT;RSVP=FALSE", str(response))


    def test_005_rescheduling_reservation(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,4,1, 10,0,0))

        response = self.check_message_received("Reservation Request for test was ACCEPTED", self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        self.purge_mailbox(self.john['mailbox'])
        self.send_itip_update(self.audi['mail'], uid, datetime.datetime(2014,4,1, 12,0,0)) # conflict with myself

        response = self.check_message_received("Reservation Request for test was ACCEPTED", self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_start().hour, 12)
        self.assertEqual(event.get_sequence(), 2)


    def test_006_cancelling_revervation(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.boxter['mail'], datetime.datetime(2014,5,1, 10,0,0))
        self.assertIsInstance(self.check_resource_calendar_event(self.boxter['kolabtargetfolder'], uid), pykolab.xml.Event)

        self.send_itip_cancel(self.boxter['mail'], uid)

        time.sleep(2)  # wait for IMAP to update
        self.assertEqual(self.check_resource_calendar_event(self.boxter['kolabtargetfolder'], uid), None)

        # make new reservation to the now free'd slot
        self.send_itip_invitation(self.boxter['mail'], datetime.datetime(2014,5,1, 9,0,0))

        response = self.check_message_received("Reservation Request for test was ACCEPTED", self.boxter['mail'])
        self.assertIsInstance(response, email.message.Message)


    def test_007_update_delegated(self):
        self.purge_mailbox(self.john['mailbox'])

        dt = datetime.datetime(2014,8,1, 12,0,0)
        uid = self.send_itip_invitation(self.cars['mail'], dt)

        # wait for accept notification
        accept = self.check_message_received("Reservation Request for test was ACCEPTED")
        self.assertIsInstance(accept, email.message.Message)
        delegatee = self.find_resource_by_email(accept['from'])

        # send update message to all attendees (collection and delegatee)
        self.purge_mailbox(self.john['mailbox'])
        update_template = itip_delegated.replace("resource-car-audia4@example.org", delegatee['mail'])
        self.send_itip_update(self.cars['mail'], uid, dt, template=update_template)
        self.send_itip_update(delegatee['mail'], uid, dt, template=update_template)

        # get response from delegatee
        accept = self.check_message_received("Reservation Request for test was ACCEPTED")
        self.assertIsInstance(accept, email.message.Message)
        self.assertIn(delegatee['mail'], accept['from'])

        # no delegation response on updates
        self.assertEqual(self.check_message_received("Reservation Request for test was DELEGATED", self.cars['mail']), None)


    def test_008_allday_reservation(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,6,2), True)

        accept = self.check_message_received("Reservation Request for test was ACCEPTED")
        self.assertIsInstance(accept, email.message.Message)

        event = self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertIsInstance(event.get_start(), datetime.date)

        uid2 = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,6,2, 16,0,0))
        response = self.check_message_received("Reservation Request for test was DECLINED", self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)


    def test_009_recurring_events(self):
        self.purge_mailbox(self.john['mailbox'])

        # register an infinitely recurring resource invitation
        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,2,20, 12,0,0),
            template=itip_recurring.replace(";COUNT=10", ""))

        accept = self.check_message_received("Reservation Request for test was ACCEPTED")
        self.assertIsInstance(accept, email.message.Message)

        # check non-recurring against recurring
        uid2 = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,3,13, 10,0,0))
        response = self.check_message_received("Reservation Request for test was DECLINED", self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        self.purge_mailbox(self.john['mailbox'])

        # check recurring against recurring
        uid3 = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,2,22, 8,0,0), template=itip_recurring)
        accept = self.check_message_received("Reservation Request for test was ACCEPTED")
        self.assertIsInstance(accept, email.message.Message)


    def test_010_invalid_bookings(self):
        self.purge_mailbox(self.john['mailbox'])

        itip_other = itip_invitation.replace("mailto:%s", "mailto:some-other-resource@example.org\nDESCRIPTION: Sent to %s")
        self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,3,22, 8,0,0), template=itip_other)

        time.sleep(1)

        itip_invalid = itip_invitation.replace("DTSTART;", "X-DTSTART;")
        self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014,3,24, 19,30,0), template=itip_invalid)

        self.assertEqual(self.check_message_received("Reservation Request for test was ACCEPTED", self.audi['mail']), None)

