import time
import pykolab
import smtplib
import email
import datetime
import uuid
import re

from pykolab.imap import IMAP
from wallace import module_resources

from pykolab.translate import _
from pykolab.xml import utils as xmlutils
from pykolab.xml import event_from_message
from pykolab.xml import participant_status_label
from pykolab.itip import events_from_message
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
UID:%s%s
DTSTAMP:20140213T125414Z
DTSTART;TZID=Europe/London:%s
DTEND;TZID=Europe/London:%s
SUMMARY:test
DESCRIPTION:test
ORGANIZER;CN="Doe, John":mailto:john.doe@example.org
ATTENDEE;ROLE=REQ-PARTICIPANT;CUTYPE=RESOURCE;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:%s
ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=TENTATIVE;CN=Somebody Else:mailto:somebody@else.com
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
UID:%s%s
DTSTAMP:20140215T125414Z
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
UID:%s%s
DTSTAMP;VALUE=DATE-TIME:20140227T141939Z
DTSTART;VALUE=DATE-TIME;TZID=Europe/London:%s
DTEND;VALUE=DATE-TIME;TZID=Europe/London:%s
SUMMARY:test
SEQUENCE:4
ATTENDEE;CN=Company Cars;PARTSTAT=DELEGATED;ROLE=NON-PARTICIPANT;CUTYPE=IND
 IVIDUAL;RSVP=TRUE;DELEGATED-TO=resource-car-audia4@example.org:mailto:reso
 urce-collection-companycars@example.org
ATTENDEE;CN=The Delegate;PARTSTAT=ACCEPTED;ROLE=REQ-PARTICIPANT;CUTYPE=INDI
 VIDUAL;RSVP=TRUE;DELEGATED-FROM=resource-collection-companycars@example.or
 g:mailto:resource-car-audia4@example.org
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
UID:%s%s
DTSTAMP:20140218T125414Z
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
UID:%s%s
DTSTAMP:20140213T125414Z
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
UID:%s%s
DTSTAMP:20140213T125414Z
DTSTART;TZID=Europe/London:%s
DTEND;TZID=Europe/London:%s
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
        # set language to default
        pykolab.translate.setUserLanguage(conf.get('kolab', 'default_locale'))

        self.itip_reply_subject = _("Reservation Request for %(summary)s was %(status)s")

        from tests.functional.purge_users import purge_users
        purge_users()

        self.john = {
            'displayname': 'John Doe',
            'mail': 'john.doe@example.org',
            'sender': 'John Doe <john.doe@example.org>',
            'mailbox': 'user/john.doe@example.org',
            'dn': 'uid=doe,ou=People,dc=example,dc=org'
        }

        self.jane = {
            'displayname': 'Jane Manager',
            'mail': 'jane.manager@example.org',
            'sender': 'Jane Manager <jane.manager@example.org>',
            'mailbox': 'user/jane.manager@example.org',
            'dn': 'uid=manager,ou=People,dc=example,dc=org'
        }

        from tests.functional.user_add import user_add
        user_add("John", "Doe", kolabinvitationpolicy='ALL_MANUAL')
        user_add("Jane", "Manager", kolabinvitationpolicy='ALL_MANUAL')

        funcs.purge_resources()
        self.audi = funcs.resource_add("car", "Audi A4")
        self.passat = funcs.resource_add("car", "VW Passat")
        self.boxter = funcs.resource_add("car", "Porsche Boxter S")
        self.cars = funcs.resource_add("collection", "Company Cars", [self.audi['dn'], self.passat['dn'], self.boxter['dn']])

        self.room1 = funcs.resource_add("confroom", "Room 101", owner=self.jane['dn'], kolabinvitationpolicy='ACT_ACCEPT_AND_NOTIFY')
        self.room2 = funcs.resource_add("confroom", "Conference Room B-222")
        self.rooms = funcs.resource_add("collection", "Rooms", [self.room1['dn'], self.room2['dn']], self.jane['dn'], kolabinvitationpolicy='ACT_ACCEPT_AND_NOTIFY')

        self.room3 = funcs.resource_add("confroom", "CEOs Office 303")
        self.viprooms = funcs.resource_add("collection", "VIP Rooms", [self.room3['dn']], self.jane['dn'], kolabinvitationpolicy='ACT_MANUAL')

        time.sleep(1)
        from tests.functional.synchronize import synchronize_once
        synchronize_once()

    def send_message(self, itip_payload, to_addr, from_addr=None):
        if from_addr is None:
            from_addr = self.john['mail']

        smtp = smtplib.SMTP('localhost', 10026)
        smtp.sendmail(from_addr, to_addr, mime_message % (to_addr, itip_payload))
        smtp.quit()

    def send_itip_invitation(self, resource_email, start=None, allday=False, template=None, uid=None, instance=None):
        if start is None:
            start = datetime.datetime.now()

        if uid is None:
            uid = str(uuid.uuid4())

        if allday:
            default_template = itip_allday
            end = start + datetime.timedelta(days=1)
            date_format = '%Y%m%d'
        else:
            end = start + datetime.timedelta(hours=4)
            default_template = itip_invitation
            date_format = '%Y%m%dT%H%M%S'

        recurrence_id = ''
        if instance is not None:
            recurrence_id = "\nRECURRENCE-ID;TZID=Europe/London:" + instance.strftime(date_format)

        self.send_message((template if template is not None else default_template) % (
                uid,
                recurrence_id,
                start.strftime(date_format),
                end.strftime(date_format),
                resource_email
            ),
            resource_email)

        return uid

    def send_itip_update(self, resource_email, uid, start=None, template=None, sequence=None, instance=None):
        if start is None:
            start = datetime.datetime.now()

        end = start + datetime.timedelta(hours=4)

        recurrence_id = ''
        if instance is not None:
            recurrence_id = "\nRECURRENCE-ID;TZID=Europe/London:" + instance.strftime('%Y%m%dT%H%M%S')

        if sequence is not None:
            if not template:
                template = itip_update
            template = re.sub(r'SEQUENCE:\d+', 'SEQUENCE:' + str(sequence), template)

        self.send_message((template if template is not None else itip_update) % (
                uid,
                recurrence_id,
                start.strftime('%Y%m%dT%H%M%S'),
                end.strftime('%Y%m%dT%H%M%S'),
                resource_email
            ),
            resource_email)

        return uid

    def send_itip_cancel(self, resource_email, uid, instance=None):
        recurrence_id = ''
        if instance is not None:
            recurrence_id = "\nRECURRENCE-ID;TZID=Europe/London:" + instance.strftime('%Y%m%dT%H%M%S')

        self.send_message(itip_cancellation % (
                uid,
                recurrence_id,
                resource_email
            ),
            resource_email)

        return uid

    def send_owner_response(self, event, partstat, from_addr=None):
        if from_addr is None:
            from_addr = self.jane['mail']

        itip_reply = event.to_message_itip(
                from_addr,
                method="REPLY",
                participant_status=partstat,
                message_text="Request " + partstat,
                subject="Booking has been %s" % (partstat)
        )

        smtp = smtplib.SMTP('localhost', 10026)
        smtp.sendmail(from_addr, str(event.get_organizer().email()), str(itip_reply))
        smtp.quit()

    def check_message_received(self, subject, from_addr=None, mailbox=None):
        if mailbox is None:
            mailbox = self.john['mailbox']

        imap = IMAP()
        imap.connect()
        imap.set_acl(mailbox, "cyrus-admin", "lrs")
        imap.imap.m.select(mailbox)

        found = None
        retries = 15

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

        imap.set_acl(mailbox, "cyrus-admin", "lrs")
        imap.imap.m.select(imap.folder_quote(mailbox))

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

                found = event_from_message(event_message)
                if found:
                    break

            time.sleep(1)

        imap.disconnect()

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
        for r in [self.audi, self.passat, self.boxter, self.room1, self.room2]:
            if (email.find(r['mail']) >= 0):
                resource = r
                break
        return resource

    def test_001_resource_from_email_address(self):
        resource = module_resources.resource_record_from_email_address(self.audi['mail'])
        self.assertEqual(len(resource), 1)
        self.assertEqual(resource[0], self.audi['dn'])

        collection = module_resources.resource_record_from_email_address(self.cars['mail'])
        self.assertEqual(len(collection), 1)
        self.assertEqual(collection[0], self.cars['dn'])

    def test_002_invite_resource(self):
        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014, 7, 13, 10, 0, 0))

        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')}, self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test")

    # @depends test_002_invite_resource
    def test_003_invite_resource_conflict(self):
        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014, 7, 13, 12, 0, 0))

        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('DECLINED')}, self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        self.assertEqual(self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid), None)

    def test_004_invite_resource_collection(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.cars['mail'], datetime.datetime(2014, 7, 13, 12, 0, 0))

        # one of the collection members accepted the reservation
        accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')})
        self.assertIsInstance(accept, email.message.Message)

        delegatee = self.find_resource_by_email(accept['from'])
        self.assertIn(delegatee['mail'], accept['from'])

        # check booking in the delegatee's resource calendar
        self.assertIsInstance(self.check_resource_calendar_event(delegatee['kolabtargetfolder'], uid), pykolab.xml.Event)

        # resource collection responds with a DELEGATED message
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('DELEGATED')}, self.cars['mail'])
        self.assertIsInstance(response, email.message.Message)
        self.assertIn("ROLE=NON-PARTICIPANT;RSVP=FALSE", str(response))

    def test_005_rescheduling_reservation(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014, 4, 1, 10, 0, 0))

        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')}, self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        self.purge_mailbox(self.john['mailbox'])
        self.send_itip_update(self.audi['mail'], uid, datetime.datetime(2014, 4, 1, 12, 0, 0))  # conflict with myself

        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')}, self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_start().hour, 12)
        self.assertEqual(event.get_sequence(), 2)

    def test_005_rescheduling_collection(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.cars['mail'], datetime.datetime(2014, 4, 24, 12, 0, 0))

        # one of the collection members accepted the reservation
        accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')})
        self.assertIsInstance(accept, email.message.Message)
        delegatee = self.find_resource_by_email(accept['from'])

        # book that resource for the next day
        self.send_itip_invitation(delegatee['mail'], datetime.datetime(2014, 4, 25, 14, 0, 0))
        accept2 = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')})

        # re-schedule first booking to a conflicting date
        self.purge_mailbox(self.john['mailbox'])
        update_template = itip_delegated.replace("resource-car-audia4@example.org", delegatee['mail'])
        self.send_itip_update(delegatee['mail'], uid, datetime.datetime(2014, 4, 25, 12, 0, 0), template=update_template)

        # expect response from another member of the initially delegated collection
        new_accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')})
        self.assertIsInstance(new_accept, email.message.Message)

        new_delegatee = self.find_resource_by_email(new_accept['from'])
        self.assertNotEqual(delegatee['mail'], new_delegatee['mail'])

        # event now booked into new delegate's calendar
        event = self.check_resource_calendar_event(new_delegatee['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)

        # old resource responds with a DELEGATED message
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('DELEGATED')}, delegatee['mail'])
        self.assertIsInstance(response, email.message.Message)

        # old reservation was removed from old delegate's calendar
        self.assertEqual(self.check_resource_calendar_event(delegatee['kolabtargetfolder'], uid), None)

    def test_006_cancelling_revervation(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.boxter['mail'], datetime.datetime(2014, 5, 1, 10, 0, 0))
        self.assertIsInstance(self.check_resource_calendar_event(self.boxter['kolabtargetfolder'], uid), pykolab.xml.Event)

        self.send_itip_cancel(self.boxter['mail'], uid)

        time.sleep(2)  # wait for IMAP to update
        self.assertEqual(self.check_resource_calendar_event(self.boxter['kolabtargetfolder'], uid), None)

        # make new reservation to the now free'd slot
        self.send_itip_invitation(self.boxter['mail'], datetime.datetime(2014, 5, 1, 9, 0, 0))

        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')}, self.boxter['mail'])
        self.assertIsInstance(response, email.message.Message)

    def test_007_update_delegated(self):
        self.purge_mailbox(self.john['mailbox'])

        dt = datetime.datetime(2014, 8, 1, 12, 0, 0)
        uid = self.send_itip_invitation(self.cars['mail'], dt)

        # wait for accept notification
        accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')})
        self.assertIsInstance(accept, email.message.Message)
        delegatee = self.find_resource_by_email(accept['from'])

        # send update message to all attendees (collection and delegatee)
        self.purge_mailbox(self.john['mailbox'])
        update_template = itip_delegated.replace("resource-car-audia4@example.org", delegatee['mail'])
        self.send_itip_update(self.cars['mail'], uid, dt, template=update_template)
        self.send_itip_update(delegatee['mail'], uid, dt, template=update_template)

        # get response from delegatee
        accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')})
        self.assertIsInstance(accept, email.message.Message)
        self.assertIn(delegatee['mail'], accept['from'])

        # no delegation response on updates
        self.assertEqual(self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('DELEGATED')}, self.cars['mail']), None)

    def test_008_allday_reservation(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014, 6, 2), True)

        accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')})
        self.assertIsInstance(accept, email.message.Message)

        event = self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertIsInstance(event.get_start(), datetime.date)

        uid2 = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014, 6, 2, 16, 0, 0))
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('DECLINED')}, self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

    def test_009_recurring_events(self):
        self.purge_mailbox(self.john['mailbox'])

        # register an infinitely recurring resource invitation
        uid = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014, 2, 20, 12, 0, 0),
            template=itip_recurring.replace(";COUNT=10", ""))

        accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')})
        self.assertIsInstance(accept, email.message.Message)

        # check non-recurring against recurring
        uid2 = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014, 3, 13, 10, 0, 0))
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('DECLINED')}, self.audi['mail'])
        self.assertIsInstance(response, email.message.Message)

        self.purge_mailbox(self.john['mailbox'])

        # check recurring against recurring
        uid3 = self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014, 2, 22, 8, 0, 0), template=itip_recurring)
        accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')})
        self.assertIsInstance(accept, email.message.Message)

    def test_010_invalid_bookings(self):
        self.purge_mailbox(self.john['mailbox'])

        itip_other = itip_invitation.replace("mailto:%s", "mailto:some-other-resource@example.org\nCOMMENT: Sent to %s")
        self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014, 3, 22, 8, 0, 0), template=itip_other)

        time.sleep(1)

        itip_invalid = itip_invitation.replace("DTSTART;", "X-DTSTART;")
        self.send_itip_invitation(self.audi['mail'], datetime.datetime(2014, 3, 24, 19, 30, 0), template=itip_invalid)

        self.assertEqual(self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')}, self.audi['mail']), None)

    def test_011_owner_info(self):
        self.purge_mailbox(self.john['mailbox'])

        self.send_itip_invitation(self.room1['mail'], datetime.datetime(2014, 6, 19, 16, 0, 0))

        accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')}, self.room1['mail'])
        self.assertIsInstance(accept, email.message.Message)
        respose_text = str(accept.get_payload(0))
        self.assertIn(self.jane['mail'], respose_text)
        self.assertIn(self.jane['displayname'], respose_text)

    def test_011_owner_info_from_collection(self):
        self.purge_mailbox(self.john['mailbox'])

        self.send_itip_invitation(self.room2['mail'], datetime.datetime(2014, 6, 19, 16, 0, 0))

        accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')}, self.room2['mail'])
        self.assertIsInstance(accept, email.message.Message)
        respose_text = str(accept.get_payload(0))
        self.assertIn(self.jane['mail'], respose_text)
        self.assertIn(self.jane['displayname'], respose_text)

    def test_012_owner_notification(self):
        self.purge_mailbox(self.john['mailbox'])
        self.purge_mailbox(self.jane['mailbox'])

        self.send_itip_invitation(self.room1['mail'], datetime.datetime(2014, 8, 4, 13, 0, 0))

        # check notification message sent to resource owner (jane)
        notify = self.check_message_received(_('Booking for %s has been %s') % (self.room1['cn'], participant_status_label('ACCEPTED')), self.room1['mail'], self.jane['mailbox'])
        self.assertIsInstance(notify, email.message.Message)

        notification_text = str(notify.get_payload())
        self.assertIn(self.john['mail'], notification_text)
        self.assertIn(participant_status_label('ACCEPTED'), notification_text)

        self.purge_mailbox(self.john['mailbox'])

        # check notification sent to collection owner (jane)
        self.send_itip_invitation(self.rooms['mail'], datetime.datetime(2014, 8, 4, 12, 30, 0))

        # one of the collection members accepted the reservation
        accepted = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')})
        delegatee = self.find_resource_by_email(accepted['from'])

        notify = self.check_message_received(_('Booking for %s has been %s') % (delegatee['cn'], participant_status_label('ACCEPTED')), delegatee['mail'], self.jane['mailbox'])
        self.assertIsInstance(notify, email.message.Message)
        self.assertIn(self.john['mail'], notification_text)

    def test_013_owner_confirmation_accept(self):
        self.purge_mailbox(self.john['mailbox'])
        self.purge_mailbox(self.jane['mailbox'])

        uid = self.send_itip_invitation(self.room3['mail'], datetime.datetime(2014, 9, 12, 14, 0, 0))

        # requester (john) gets a TENTATIVE confirmation
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('TENTATIVE')}, self.room3['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_resource_calendar_event(self.room3['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_summary(), "test")
        self.assertEqual(event.get_attendee_by_email(self.room3['mail']).get_participant_status(True), 'TENTATIVE')

        # check confirmation message sent to resource owner (jane)
        notify = self.check_message_received(_('Booking request for %s requires confirmation') % (self.room3['cn']), mailbox=self.jane['mailbox'])
        self.assertIsInstance(notify, email.message.Message)

        # resource owner confirms reservation request
        itip_event = events_from_message(notify)[0]
        self.send_owner_response(itip_event['xml'], 'ACCEPTED', from_addr=self.jane['mail'])

        # requester (john) now gets the ACCEPTED response
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')}, self.room3['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_resource_calendar_event(self.room3['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_status(True), 'CONFIRMED')
        self.assertEqual(event.get_attendee_by_email(self.room3['mail']).get_participant_status(True), 'ACCEPTED')

    def test_014_owner_confirmation_decline(self):
        self.purge_mailbox(self.john['mailbox'])
        self.purge_mailbox(self.jane['mailbox'])

        uid = self.send_itip_invitation(self.room3['mail'], datetime.datetime(2014, 9, 14, 9, 0, 0))

        # requester (john) gets a TENTATIVE confirmation
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('TENTATIVE')}, self.room3['mail'])
        self.assertIsInstance(response, email.message.Message)

        # check confirmation message sent to resource owner (jane)
        notify = self.check_message_received(_('Booking request for %s requires confirmation') % (self.room3['cn']), mailbox=self.jane['mailbox'])
        self.assertIsInstance(notify, email.message.Message)

        itip_event = events_from_message(notify)[0]

        # resource owner declines reservation request
        itip_reply = itip_event['xml'].to_message_itip(
                self.jane['mail'],
                method="REPLY",
                participant_status='DECLINED',
                message_text="Request declined",
                subject=_('Booking for %s has been %s') % (self.room3['cn'], participant_status_label('DECLINED'))
        )

        smtp = smtplib.SMTP('localhost', 10026)
        smtp.sendmail(self.jane['mail'], str(itip_event['organizer']), str(itip_reply))
        smtp.quit()

        # requester (john) now gets the DECLINED response
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('DECLINED')}, self.room3['mail'])
        self.assertIsInstance(response, email.message.Message)

        # tentative reservation was set to cancelled
        event = self.check_resource_calendar_event(self.room3['kolabtargetfolder'], uid)
        self.assertEqual(event, None)
        # self.assertEqual(event.get_status(True), 'CANCELLED')
        # self.assertEqual(event.get_attendee_by_email(self.room3['mail']).get_participant_status(True), 'DECLINED')

    def test_015_owner_confirmation_update(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.room3['mail'], datetime.datetime(2014, 8, 19, 9, 0, 0), uid="http://a-totally.stupid/?uid")

        # requester (john) gets a TENTATIVE confirmation
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('TENTATIVE')}, self.room3['mail'])
        self.assertIsInstance(response, email.message.Message)

        # check first confirmation message sent to resource owner (jane)
        notify1 = self.check_message_received(_('Booking request for %s requires confirmation') % (self.room3['cn']), mailbox=self.jane['mailbox'])
        self.assertIsInstance(notify1, email.message.Message)

        itip_event1 = events_from_message(notify1)[0]
        self.assertEqual(itip_event1['start'].hour, 9)

        self.purge_mailbox(self.jane['mailbox'])
        self.purge_mailbox(self.john['mailbox'])

        # send update with new date (and sequence)
        self.send_itip_update(self.room3['mail'], uid, datetime.datetime(2014, 8, 19, 16, 0, 0))

        event = self.check_resource_calendar_event(self.room3['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_attendee_by_email(self.room3['mail']).get_participant_status(True), 'TENTATIVE')

        # check second confirmation message sent to resource owner (jane)
        notify2 = self.check_message_received(_('Booking request for %s requires confirmation') % (self.room3['cn']), mailbox=self.jane['mailbox'])
        self.assertIsInstance(notify2, email.message.Message)

        itip_event2 = events_from_message(notify2)[0]
        self.assertEqual(itip_event2['start'].hour, 16)

        # resource owner declines the first reservation request
        itip_reply = itip_event1['xml'].to_message_itip(
                self.jane['mail'],
                method="REPLY",
                participant_status='DECLINED',
                message_text="Request declined",
                subject=_('Booking for %s has been %s') % (self.room3['cn'], participant_status_label('DECLINED'))
        )
        smtp = smtplib.SMTP('localhost', 10026)
        smtp.sendmail(self.jane['mail'], str(itip_event1['organizer']), str(itip_reply))
        smtp.quit()

        time.sleep(5)

        # resource owner accpets the second reservation request
        itip_reply = itip_event2['xml'].to_message_itip(
                self.jane['mail'],
                method="REPLY",
                participant_status='ACCEPTED',
                message_text="Request accepred",
                subject=_('Booking for %s has been %s') % (self.room3['cn'], participant_status_label('ACCEPTED'))
        )
        smtp = smtplib.SMTP('localhost', 10026)
        smtp.sendmail(self.jane['mail'], str(itip_event2['organizer']), str(itip_reply))
        smtp.quit()

        # requester (john) now gets the ACCEPTED response
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('ACCEPTED')}, self.room3['mail'])
        self.assertIsInstance(response, email.message.Message)

        event = self.check_resource_calendar_event(self.room3['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(event.get_attendee_by_email(self.room3['mail']).get_participant_status(True), 'ACCEPTED')

    def test_016_collection_owner_confirmation(self):
        self.purge_mailbox(self.john['mailbox'])

        uid = self.send_itip_invitation(self.viprooms['mail'], datetime.datetime(2014, 8, 15, 17, 0, 0))

        # resource collection responds with a DELEGATED message
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('DELEGATED')}, self.viprooms['mail'])
        self.assertIsInstance(response, email.message.Message)

        # the collection member tentatively accepted the reservation
        accept = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('TENTATIVE')})
        self.assertIsInstance(accept, email.message.Message)
        self.assertIn(self.room3['mail'], accept['from'])

        # check confirmation message sent to resource owner (jane)
        notify = self.check_message_received(_('Booking request for %s requires confirmation') % (self.room3['cn']), mailbox=self.jane['mailbox'])
        self.assertIsInstance(notify, email.message.Message)

    def test_017_reschedule_single_occurrence(self):
        self.purge_mailbox(self.john['mailbox'])

        subject = {'summary': 'test', 'status': participant_status_label('ACCEPTED')}
        subject = self.itip_reply_subject % (subject)

        # register a recurring resource invitation
        start = datetime.datetime(2015, 2, 10, 12, 0, 0)
        uid = self.send_itip_invitation(self.audi['mail'], start, template=itip_recurring)

        accept = self.check_message_received(subject)
        self.assertIsInstance(accept, email.message.Message)

        self.purge_mailbox(self.john['mailbox'])

        # send rescheduling request to a single instance
        exdate = start + datetime.timedelta(days=14)
        exstart = exdate + datetime.timedelta(hours=5)
        self.send_itip_update(self.audi['mail'], uid, exstart, instance=exdate)

        accept = self.check_message_received(subject)
        self.assertIsInstance(accept, email.message.Message)
        self.assertIn("RECURRENCE-ID;TZID=Europe/London:" + exdate.strftime('%Y%m%dT%H%M%S'), str(accept))

        event = self.check_resource_calendar_event(self.audi['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(len(event.get_exceptions()), 1)

        # send new invitation for now free slot
        uid = self.send_itip_invitation(self.audi['mail'], exdate, template=itip_invitation.replace('SUMMARY:test', 'SUMMARY:new'))

        accept = self.check_message_received(subject)
        self.assertIsInstance(accept, email.message.Message)

        # send rescheduling request to that single instance again: now conflicting
        exdate = start + datetime.timedelta(days=14)
        exstart = exdate + datetime.timedelta(hours=2)
        self.send_itip_update(self.audi['mail'], uid, exstart, instance=exdate, sequence=3)

        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('DECLINED')})
        self.assertIsInstance(response, email.message.Message)
        self.assertIn("RECURRENCE-ID;TZID=Europe/London:", str(response))

    def test_018_invite_single_occurrence(self):
        self.purge_mailbox(self.john['mailbox'])
        self.purge_mailbox(self.boxter['kolabtargetfolder'])

        subject = {'summary': 'test', 'status': participant_status_label('ACCEPTED')}
        subject = self.itip_reply_subject % (subject)

        start = datetime.datetime(2015, 3, 2, 18, 30, 0)
        uid = self.send_itip_invitation(self.boxter['mail'], start, instance=start)

        accept = self.check_message_received(subject)
        self.assertIsInstance(accept, email.message.Message)
        self.assertIn("RECURRENCE-ID;TZID=Europe/London:" + start.strftime('%Y%m%dT%H%M%S'), str(accept))

        self.purge_mailbox(self.john['mailbox'])

        # send a second invitation for another instance with the same UID
        nextstart = datetime.datetime(2015, 3, 9, 18, 30, 0)
        self.send_itip_invitation(self.boxter['mail'], nextstart, uid=uid, instance=nextstart)

        accept = self.check_message_received(subject)
        self.assertIsInstance(accept, email.message.Message)
        self.assertIn("RECURRENCE-ID;TZID=Europe/London:" + nextstart.strftime('%Y%m%dT%H%M%S'), str(accept))

        self.purge_mailbox(self.john['mailbox'])

        # send rescheduling request to the first instance
        exstart = start + datetime.timedelta(hours=2)
        self.send_itip_update(self.boxter['mail'], uid, exstart, instance=start)

        accept = self.check_message_received(subject)
        self.assertIsInstance(accept, email.message.Message)
        self.assertIn("RECURRENCE-ID;TZID=Europe/London:" + start.strftime('%Y%m%dT%H%M%S'), str(accept))

        # the resource calendar now has two reservations stored in one object
        one = self.check_resource_calendar_event(self.boxter['kolabtargetfolder'], uid)
        self.assertIsInstance(one, pykolab.xml.Event)
        self.assertIsInstance(one.get_recurrence_id(), datetime.datetime)
        self.assertEqual(one.get_start().hour, exstart.hour)

        two = one.get_instance(nextstart)
        self.assertIsInstance(two, pykolab.xml.Event)
        self.assertIsInstance(two.get_recurrence_id(), datetime.datetime)

        self.purge_mailbox(self.john['mailbox'])

        # send rescheduling request to the 2nd instance
        self.send_itip_update(self.boxter['mail'], uid, nextstart + datetime.timedelta(hours=2), sequence=2, instance=nextstart)

        accept = self.check_message_received(subject)
        self.assertIsInstance(accept, email.message.Message)
        self.assertIn("RECURRENCE-ID;TZID=Europe/London:" + nextstart.strftime('%Y%m%dT%H%M%S'), str(accept))

        event = self.check_resource_calendar_event(self.boxter['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(len(event.get_exceptions()), 1)

        two = event.get_instance(nextstart)
        self.assertIsInstance(two, pykolab.xml.Event)
        self.assertEqual(two.get_sequence(), 2)
        self.assertEqual(two.get_start().hour, 20)

    def test_019_cancel_single_occurrence(self):
        self.purge_mailbox(self.john['mailbox'])

        subject = {'summary': 'test', 'status': participant_status_label('ACCEPTED')}
        subject = self.itip_reply_subject % (subject)

        # register a recurring resource invitation
        start = datetime.datetime(2015, 2, 12, 14, 0, 0)
        uid = self.send_itip_invitation(self.passat['mail'], start, template=itip_recurring)

        accept = self.check_message_received(subject)
        self.assertIsInstance(accept, email.message.Message)

        exdate = start + datetime.timedelta(days=7)
        self.send_itip_cancel(self.passat['mail'], uid, instance=exdate)

        time.sleep(5)  # wait for IMAP to update
        event = self.check_resource_calendar_event(self.passat['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(len(event.get_exceptions()), 1)

        exception = event.get_instance(exdate)
        self.assertEqual(exception.get_status(True), 'CANCELLED')
        self.assertTrue(exception.get_transparency())

        self.purge_mailbox(self.john['mailbox'])

        # store a single occurrence with recurrence-id
        start = datetime.datetime(2015, 3, 2, 18, 30, 0)
        uid = self.send_itip_invitation(self.passat['mail'], start, instance=start)

        accept = self.check_message_received(subject)
        self.assertIsInstance(accept, email.message.Message)

        self.send_itip_cancel(self.passat['mail'], uid, instance=start)

        time.sleep(5)  # wait for IMAP to update
        self.assertEqual(self.check_resource_calendar_event(self.passat['kolabtargetfolder'], uid), None)

    def test_020_owner_confirmation_single_occurrence(self):
        self.purge_mailbox(self.john['mailbox'])
        self.purge_mailbox(self.jane['mailbox'])

        start = datetime.datetime(2015, 4, 18, 14, 0, 0)
        uid = self.send_itip_invitation(self.room3['mail'], start, template=itip_recurring)

        notify = self.check_message_received(_('Booking request for %s requires confirmation') % (self.room3['cn']), mailbox=self.jane['mailbox'])
        self.assertIsInstance(notify, email.message.Message)

        # resource owner confirms reservation request (entire series)
        itip_event = events_from_message(notify)[0]
        self.send_owner_response(itip_event['xml'], 'ACCEPTED', from_addr=self.jane['mail'])

        self.purge_mailbox(self.john['mailbox'])
        self.purge_mailbox(self.jane['mailbox'])

        # send rescheduling request to a single instance
        exdate = start + datetime.timedelta(days=14)
        exstart = exdate + datetime.timedelta(hours=4)
        self.send_itip_update(self.room3['mail'], uid, exstart, instance=exdate)

        # check confirmation message sent to resource owner (jane)
        notify = self.check_message_received(_('Booking request for %s requires confirmation') % (self.room3['cn']), mailbox=self.jane['mailbox'])
        self.assertIsInstance(notify, email.message.Message)
        self.assertIn("RECURRENCE-ID;TZID=Europe/London:" + exdate.strftime('%Y%m%dT%H%M%S'), str(notify))

        itip_event = events_from_message(notify)[0]
        self.assertIsInstance(itip_event['xml'].get_recurrence_id(), datetime.datetime)

        # resource owner declines reservation request
        self.send_owner_response(itip_event['xml'], 'DECLINED', from_addr=self.jane['mail'])

        # requester (john) now gets the DECLINED response
        response = self.check_message_received(self.itip_reply_subject % {'summary': 'test', 'status': participant_status_label('DECLINED')}, self.room3['mail'])
        self.assertIsInstance(response, email.message.Message)
        self.assertIn("RECURRENCE-ID;TZID=Europe/London:" + exdate.strftime('%Y%m%dT%H%M%S'), str(response))

        event = self.check_resource_calendar_event(self.room3['kolabtargetfolder'], uid)
        self.assertIsInstance(event, pykolab.xml.Event)
        self.assertEqual(len(event.get_exceptions()), 1)

        exception = event.get_instance(exdate)
        self.assertEqual(exception.get_attendee_by_email(self.room3['mail']).get_participant_status(True), 'DECLINED')
