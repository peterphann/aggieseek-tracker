import time
import firebase_admin
from firebase_admin import credentials, db
import logging
import notifications
import embed
from logging_config import init_logging
from datetime import datetime, timezone
from section import get_section_info
import os
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)
CURRENT_TERM = os.getenv('CURRENT_TERM')
BATCH_SIZE = int(os.getenv('BATCH_SIZE'), 10)

def split_list(arr, batch_size):
    return [arr[i:i + batch_size] for i in range(0, len(arr), batch_size)]

class SectionMonitor:
    def __init__(self, term):

        if not firebase_admin._apps:
            cred = credentials.Certificate(os.getenv('CERTIFICATE_PATH'))
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.getenv('DATABASE_URL')
            })

        self.term = term
        self.crns = self.get_tracked_sections()
        self.sections = db.reference(f'sections/{self.term}/').get()
        self.users = db.reference('users/').get()
        self.start_time = datetime.strftime(datetime.now(timezone.utc), "%Y-%m-%dT%H:%M:%SZ")

    def get_tracked_sections(self):
        ref = db.reference(f'sections/{self.term}/')
        if not ref.get():
            return []
        sections = ref.get().keys()
        return sections
    
    async def check_change(self, crn):
        section = await get_section_info(self.term, crn)
        if not section:
            logging.info(f'Section {crn} is invalid, skipping over')
            return
        
        logging.info(f'Fetched section {crn}, {section["SUBJECT_CODE"]} {section["COURSE_NUMBER"]} - {section["COURSE_TITLE"]}')
        
        crn = section['CRN']
        seats_ref = db.reference(f'sections/{self.term}/{crn}/seats')

        if self.sections[crn].get('users', None) is None:
            logging.info(f'Section {crn} has no active users, removing from database')
            db.reference(f'sections/{self.term}/{crn}').delete()
            return
        
        prev_seats = self.sections[crn].get('seats', None)
        curr_seats = section['SEATS']['REMAINING']

        if prev_seats != curr_seats:
            seats_ref.set(curr_seats)
            if prev_seats is None:
                return
            logging.info(f'Change detected in section {crn}, {section["SUBJECT_CODE"]} {section["COURSE_NUMBER"]} - {section["COURSE_TITLE"]}, {prev_seats} to {curr_seats}')
            self.notify(crn, prev_seats, section)

    def notify(self, crn, prev, section):
        curr = section["SEATS"]["REMAINING"]
        logging.info(f'Detected change in section {crn}, from {prev} to {curr}')

        tracking_users = self.sections[crn].get('users', {})

        for uid in tracking_users:
            user = self.users[uid]
            if 'methods' not in user:
                continue

            noti_mode = "all" # Default notification mode if user doesn't have one selected
            methods = user['methods'] 
            if 'settings' in user:
                noti_mode = user['settings'].get('notificationMode', 'all')

            if noti_mode != "all" and not (prev <= 0 < curr):
                continue

            notifications.generate_notification(uid, section, prev)

            if methods['discord']['enabled']:
                webhook_url = methods['discord']['value']
                discord_embed = embed.update_embed(section, prev)

                status_code = notifications.send_discord(webhook_url, discord_embed)
                if status_code != 200 and status_code != 204:
                    logging.warning(f'Discord alert sent to user {uid}, status code {status_code}')
                else:
                    logging.info(f'Discord alert sent to user {uid}, status code {status_code}')

            if methods['phone']['enabled']:
                phone_number = methods['phone']['value']
                notifications.send_message(phone_number, section, prev)
                logging.info(f'Phone alert sent to user {uid}, {phone_number}')

            if methods['email']['enabled']:
                # TODO: Handle email alert
                email_address = methods['email']['value']
                logging.info(f'Email alert sent to user {uid}, {email_address}')

def main():
    init_logging()
    monitor = SectionMonitor(CURRENT_TERM)
    crns = list(monitor.get_tracked_sections())
    batches = split_list(crns, BATCH_SIZE)
    
    async def monitor_sections(crns):
        tasks = []
        for crn in crns:
            tasks.append(monitor.check_change(crn))
        await asyncio.gather(*tasks)
        logging.info(f'Checked batch {crns} in {time.time() - start_time:.2f} secs')

    start_time = time.time()
    for batch in batches:
        try:
            asyncio.run(monitor_sections(batch))
        except Exception as e:
            logging.critical(f'Exception raised while running batch: {e}')

    runtime = time.time() - start_time
    logging.info(f'RUN FINISHED: {runtime:.2f} secs / {len(crns)} sections | {len(crns) / runtime:.2f} sections / sec | {BATCH_SIZE} batch size')

if __name__ == '__main__':
    main()
    
