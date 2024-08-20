import time
import firebase_admin
from firebase_admin import credentials, db
import requests
import logging
import notifications
import embed
import concurrent.futures
from datetime import datetime

def configure_logging() -> None:
    logging.getLogger().setLevel(logging.INFO)


class SectionMonitor:
    def __init__(self, certificate_path, database_url):
        self.cred = credentials.Certificate(certificate_path)
        self.duplicates = set()
        self.sections = {}
        firebase_admin.initialize_app(self.cred, {
            'databaseURL': database_url
        })
        self.run = db.reference(f'runs/{datetime.strftime(datetime.utcnow(), "%Y-%m-%dT%H:%M:%SZ")}/')
        self.run.set(-1)

    def get_tracked_sections(self):
        ref = db.reference('sections/')
        sections = ref.get().keys()
        return sections

    def log_time(self, time):
        self.run.set(time)

    def get_section(self, crn) -> {}:
        section_url = f'https://api.aggieseek.net/sections/202431/{crn}/'
        request = requests.get(section_url)

        if request.status_code != 200:
            logging.error(f'Failed to get section {crn}')
            return False

        return request.json()

    def check_batch(self, batch):
        sections = self.get_section(batch)
        for section in sections:
            self.sections[section['crn']] = section
            self.check_change(section['crn'])

    def check_change(self, crn):
        seats_ref = db.reference(f'sections/{crn}/seats')
        users_ref = db.reference(f'sections/{crn}/users')

        section = self.sections[crn]
        if users_ref.get() is None:
            logging.info(f'Section {crn} has no active users, removing')
            db.reference(f'sections/{crn}').delete()
            return
        if not section:
            logging.info(f'Section {crn} is invalid')
            return

        logging.info(f'Checking section {crn}, {section["course"]} - {section["title"]}')
        prev_seats = seats_ref.get()
        curr_seats = section['seats']['remaining']

        seats_ref.set(curr_seats)

        if prev_seats != curr_seats and prev_seats is not None:
            self.notify(crn, prev_seats)

    def get_firebase_settings(self):
        settings_ref = db.reference('settings/')
        settings = settings_ref.get()
        return settings

    def notify(self, crn, prev):
        ref = db.reference(f'sections/{crn}/users')

        section = self.sections[crn]
        logging.info(f'Detected change in section {crn}, from {prev} to {section["seats"]["remaining"]}')
        users = ref.get()
        if not section:
            return

        discord_embed = embed.update_embed(section, prev)
        for user in users:
            user_ref = db.reference(f'users/{user}/methods')
            methods = user_ref.get()

            notifications.generate_notification(user, section, prev)

            if methods['discord']['enabled']:
                webhook_url = methods['discord']['value']

                instance = (crn, webhook_url)
                if instance not in self.duplicates:
                    status_code = notifications.send_discord(webhook_url, discord_embed)
                    logging.info(f'Discord alert sent to user {user}, status code {status_code}')
                    self.duplicates.add(instance)

            if methods['phone']['enabled']:
                phone_number = methods['phone']['value']
                notifications.send_message(phone_number, section, prev)
                logging.info(f'Phone alert sent to user {user}')

            if methods['email']['enabled']:
                # TODO: Handle email alert
                logging.info(f'Email alert sent to user {user}')


def handler(event, context):
    start = time.time()
    configure_logging()
    monitor = SectionMonitor('aggieseek-firebase-adminsdk-4uuf9-c5ed290f9a.json',
                             'https://aggieseek-default-rtdb.firebaseio.com')

    settings = monitor.get_firebase_settings()

    logging.info(settings)
    crns = list(monitor.get_tracked_sections())
    batch_size = settings['server_batch_size']

    batches = [crns[i:i + batch_size] for i in range(0, len(crns), batch_size)]
    batches = [','.join(batch) for batch in batches]

    with concurrent.futures.ThreadPoolExecutor(max_workers=settings['executor_workers']) as executor:
        for batch in batches:
            executor.submit(monitor.check_batch, batch)

    runtime = float(f'{time.time() - start:.2f}')
    monitor.log_time(runtime)
    logging.info(f'Finished in {runtime} seconds.')


if __name__ == '__main__':
    handler(None, None)
