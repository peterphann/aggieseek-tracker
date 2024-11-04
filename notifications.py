from datetime import datetime
import requests
from twilio.rest import Client
import os
from dotenv import load_dotenv
from embed import seats_embed, instructor_embed
import logging
from firebase_admin import db

from enum import Enum

load_dotenv(override=True)

# Twilio keys
ACCOUNT_SID = os.getenv(
    'ACCOUNT_SID')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

# Mailgun keys
MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
MAILGUN_API_URL = "https://api.mailgun.net/v3/email.aggieseek.net/messages"
FROM_EMAIL_ADDRESS = "AggieSeek <no-reply@email.aggieseek.net>"

PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'off')

production = PRODUCTION_MODE == 'on'
print(f'You are running in {"production" if production else "development"} mode.')


twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)
twilio_logger = logging.getLogger('twilio.http_client')
twilio_logger.setLevel(logging.DEBUG)

def get_keyword(prev, curr):
    if prev <= 0 < curr:
        keyword = "✅", "opened"
    elif prev >= 1 and curr <= 0:
        keyword = "❌", "closed"
    elif prev > curr:
        keyword = "📉", "decreased"
    elif prev < curr:
        keyword = "📈", "increased"
    else:
        keyword = "‼️", "changed"

    return keyword

class NotiType(Enum):
    TEXT, DISCORD, EMAIL = range(3)

class Notification:
    def __init__(self, section: dict, previous, current, noti_type: NotiType, destination: str):
        self.section = section
        self.previous = previous
        self.current = current
        self.type = noti_type
        self.destination = destination

    def to_tuple(self):
        return (self.section['CRN'], self.previous, self.current, self.type, self.destination)

    def send(self):
        if self.type == NotiType.TEXT:
            message = self.generate_text()
            self.send_text(message)
        elif self.type == NotiType.DISCORD:
            embed = self.generate_discord()
            self.send_discord(embed)
        elif self.type == NotiType.EMAIL:
            pass
            # subject, message = self.generate_email()
            # self.send_email(subject, message)

    def send_text(self, message):
        logging.info(f'Sending text message to {self.destination}')
        if not production: return

        message = twilio_client.messages.create(
            from_=PHONE_NUMBER,
            body=message,
            to=self.destination
        )

        return message.sid

    def send_email(self, subject, message):
        logging.info(f'Sending email to {self.destination}')
        if not production: return

        try:
            post_request = requests.post(MAILGUN_API_URL, auth=("api", MAILGUN_API_KEY),
                                        data={
                                            "from": FROM_EMAIL_ADDRESS,
                                            "to": self.destination,
                                            "subject": subject,
                                            "text": message
                                        })
            if post_request.status_code == 200:
                logging.info(f'Successfully sent an email to {self.destination} via Mailgun API.')
            else:
                logging.error(f'Could not send the email to {self.destination}, reason: {post_request.text}')
        except Exception as ex:
            logging.exception(f'Mailgun error: {ex}')

    def send_discord(self, embed):
        logging.info(f'Sending discord message to {self.destination}')
        if not production: return
    
        post_request = requests.post(self.destination, json=embed)
        status_code = post_request.status_code

        return status_code

class SeatNotification(Notification):
    def generate_text(self):
        emoji, text = get_keyword(self.previous, self.current)
        course = self.section['SUBJECT_CODE'] + " " + self.section['COURSE_NUMBER']
        return f"{emoji} {course} / {self.section['COURSE_TITLE']} / {self.section['CRN']}\n{self.section['INSTRUCTOR']} {text}!\n{self.previous} -> {self.current}"
    
    def generate_discord(self):
        return seats_embed(self.section, self.previous, self.current)
    
    def generate_email(self):
        pass

class InstructorNotification(Notification):
    def generate_text(self):
        course = self.section['SUBJECT_CODE'] + " " + self.section['COURSE_NUMBER']
        return f"{course} / {self.section['COURSE_TITLE']} / {self.section['CRN']}\nInstructor has changed!\n{self.previous} -> {self.current}"
    
    def generate_discord(self):
        return instructor_embed(self.section, self.previous, self.current)

    def generate_email(self):
        pass

def generate_seat_web(uid, section, previous, current):
    if not production: return

    timestamp = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%SZ')
    db_ref = db.reference(f'users/{uid}/notifications/{timestamp} {section["CRN"]}')

    db_ref.set({
        'title': section['SUBJECT_CODE'] + " " + section['COURSE_NUMBER'],
        'timestamp': timestamp,
        'crn': section['CRN'],
        'message': f'Seats {get_keyword(previous, current)[1]}',
        'origSeats': previous,
        'newSeats': current
    })

def generate_instructor_web(uid, section, previous, current):
    if not production: return

    timestamp = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%SZ')
    db_ref = db.reference(f'users/{uid}/notifications/{timestamp} {section["CRN"]}')

    db_ref.set({
        'title': section['SUBJECT_CODE'] + " " + section['COURSE_NUMBER'],
        'timestamp': timestamp,
        'crn': section['CRN'],
        'message': f'Instructor changed',
        'origSeats': previous,
        'newSeats': current
    })