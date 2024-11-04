import time
import firebase_admin
from firebase_admin import credentials, db
import logging
from notifications import SeatNotification, InstructorNotification, NotiType, generate_seat_web, generate_instructor_web
from logging_config import init_logging
from section import get_section_info
import os
import asyncio
from embed import error_embed
import requests
from dotenv import load_dotenv

load_dotenv(override=True)
CURRENT_TERM = os.getenv('CURRENT_TERM')
BATCH_SIZE = int(os.getenv('BATCH_SIZE'), 10)
CERTIFICATE_PATH = os.getenv('CERTIFICATE_PATH')
DATABASE_URL = os.getenv('DATABASE_URL')
CONSOLE_URL = os.getenv('CONSOLE_URL')

def split_list(arr, batch_size):
    return [arr[i:i + batch_size] for i in range(0, len(arr), batch_size)]

class SectionMonitor:
    def __init__(self, term):
        if not firebase_admin._apps:
            cred = credentials.Certificate(CERTIFICATE_PATH)
            firebase_admin.initialize_app(cred, {
                'databaseURL': DATABASE_URL
            })

        self.term = term
        self.sections = db.reference(f'sections/{self.term}/').get()
        self.users = db.reference('users/').get()

        self.seen = set()
        self.notifications = []

    async def check_change(self, crn):
        section = await get_section_info(self.term, crn)
        if not section:
            logging.warn(f'Section {crn} is invalid, skipping over')
            return
        
        logging.debug(f'Fetched section {crn}, {section["SUBJECT_CODE"]} {section["COURSE_NUMBER"]} - {section["COURSE_TITLE"]}')
        
        crn = section['CRN']

        if self.sections[crn].get('users', None) is None:
            logging.info(f'Section {crn} has no active users, removing from database')
            db.reference(f'sections/{self.term}/{crn}').delete()
            return
        
        prev_seats = self.sections[crn].get('seats', None)
        curr_seats = section['SEATS']['REMAINING']
        prev_instructor = self.sections[crn].get('instructor', None)
        curr_instructor = section['INSTRUCTOR']

        if prev_seats != curr_seats:
            seats_ref = db.reference(f'sections/{self.term}/{crn}/seats')
            seats_ref.set(curr_seats)
            if prev_seats is not None:
                self.create_seats_noti(section, prev_seats, curr_seats)

        if prev_instructor != curr_instructor:
            instructor_ref = db.reference(f'sections/{self.term}/{crn}/instructor')
            instructor_ref.set(curr_instructor)
            if prev_instructor is not None:
                self.create_instructor_noti(section, prev_instructor, curr_instructor)

    def create_seats_noti(self, section, previous, current):
        logging.info(f'Detected seats change in section {section['CRN']}, from {previous} to {current}')
        tracking_users = self.sections[section['CRN']].get('users', {})

        for uid in tracking_users:
            user = self.users[uid]
            if 'methods' not in user:
                logging.warning(f'User {uid} does not have methods field, skipping')
                continue

            if 'settings' not in user:
                logging.warning(f'User {uid} does not have settings field, skipping')
                continue

            conditions = user['settings']['notificationModes']

            if (conditions['open'] and previous <= 0 < current) or (conditions['close'] and current <= 0 < previous):
                methods = user['methods']
                generate_seat_web(uid, section, previous, current)

                if methods['discord']['enabled']:
                    webhook_url = methods['discord']['value']
                    notification = SeatNotification(section, previous, current, NotiType.DISCORD, webhook_url)
                    self.add_notification(notification)

                if methods['phone']['enabled']:
                    phone_number = methods['phone']['value']
                    notification = SeatNotification(section, previous, current, NotiType.TEXT, phone_number)
                    self.add_notification(notification)

                if methods['email']['enabled']:
                    email_address = methods['email']['value']
                    notification = SeatNotification(section, previous, current, NotiType.EMAIL, email_address)
                    self.add_notification(notification)

    def create_instructor_noti(self, section, previous, current):
        logging.info(f'Detected instructor change in section {section['CRN']}, from {previous} to {current}')
        tracking_users = self.sections[section['CRN']].get('users', {})

        for uid in tracking_users:
            user = self.users[uid]
            if 'methods' not in user:
                logging.warning(f'User {uid} does not have methods field, skipping')
                continue

            if 'settings' not in user:
                logging.warning(f'User {uid} does not have settings field, skipping')
                continue

            tracking = user['settings']['notificationModes'].get('instructors', False)
            if not tracking: continue


            methods = user['methods']
            generate_instructor_web(uid, section, previous, current)

            if methods['discord']['enabled']:
                webhook_url = methods['discord']['value']
                notification = InstructorNotification(section, previous, current, NotiType.DISCORD, webhook_url)
                self.add_notification(notification)

            if methods['phone']['enabled']:
                phone_number = methods['phone']['value']
                notification = InstructorNotification(section, previous, current, NotiType.TEXT, phone_number)
                self.add_notification(notification)

            if methods['email']['enabled']:
                email_address = methods['email']['value']
                notification = InstructorNotification(section, previous, current, NotiType.EMAIL, email_address)
                self.add_notification(notification)

    def add_notification(self, notification):
        if (notification.to_tuple() not in self.seen):
            self.seen.add(notification.to_tuple())
            self.notifications.append(notification)
            
    def send_notifications(self):
        for notification in self.notifications:
            notification.send()

    
def main():
    init_logging()
    monitor = SectionMonitor(CURRENT_TERM)
    crns = list(monitor.sections.keys())
    batches = split_list(crns, BATCH_SIZE)
    start_time = time.time()
    
    logging.info(f'Beginning new run / {len(crns)} sections')
    
    async def monitor_sections(crns):
        tasks = [monitor.check_change(crn) for crn in crns]
        await asyncio.gather(*tasks)

    try:
        for batch in batches:
            start_batch_time = time.time()
            asyncio.run(monitor_sections(batch))
            logging.info(f'Checked batch {batch} in {time.time() - start_batch_time:.2f} secs')
        monitor.send_notifications()
    except Exception as e:
        logging.exception(f'Exception raised while running batch: {e}')
        requests.post(CONSOLE_URL, json=error_embed(e))
        time.sleep(10) # If error, wait 10 seconds before continuing
    
    runtime = time.time() - start_time
    logging.info(f'RUN FINISHED: {runtime:.2f} secs / {len(crns)} sections | {len(crns) / runtime:.2f} sections / sec | {BATCH_SIZE} batch size')

if __name__ == '__main__':
    main()
