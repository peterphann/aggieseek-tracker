import time
import firebase_admin
from firebase_admin import credentials, db
import requests
import logging
import notifications
import embed
import concurrent.futures


def configure_logging() -> None:
    logging.getLogger().setLevel(logging.INFO)


class SectionMonitor:
    def __init__(self, certificate_path, database_url):
        self.cred = credentials.Certificate(certificate_path)
        self.duplicates = set()
        firebase_admin.initialize_app(self.cred, {
            'databaseURL': database_url
        })

    def get_tracked_sections(self):
        ref = db.reference('sections/')
        sections = ref.get().keys()
        return sections

    def get_section(self, crn) -> {}:
        section_url = f'http://api.aggieseek.net/sections/202431/{crn}/'
        request = requests.get(section_url)

        if request.status_code != 200:
            logging.error(f'Failed to get section {crn}')
            return False

        return request.json()

    def check_change(self, crn):
        seats_ref = db.reference(f'sections/{crn}/seats')
        users_ref = db.reference(f'sections/{crn}/users')

        section = self.get_section(crn)
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


    def notify(self, crn, prev):
        ref = db.reference(f'sections/{crn}/users')

        section = self.get_section(crn)
        logging.info(f'Detected change in section {crn}, from {prev} to {section["seats"]["remaining"]}')
        users = ref.get()
        if not section:
            return

        discord_embed = embed.update_embed(section, prev)
        for user in users:
            user_ref = db.reference(f'users/{user}/methods')
            methods = user_ref.get()

            if methods['discord']['enabled']:
                webhook_url = methods['discord']['value']

                instance = (crn, webhook_url)
                if instance not in dupes:
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


def main():
    configure_logging()
    monitor = SectionMonitor('aggieseek-firebase-adminsdk-4uuf9-c5ed290f9a.json', '')

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for crn in crns:
            executor.submit(check_change, crn)


if __name__ == '__main__':
    main()
