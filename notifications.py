import requests
from firebase_admin import db
from twilio.rest import Client
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
ACCOUNT_SID = os.getenv(
    'ACCOUNT_SID')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
client = Client(ACCOUNT_SID, AUTH_TOKEN)


def generate_notification(user, section, prev):
    timestamp = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%SZ')
    db_ref = db.reference(f'users/{user}/notifications/{timestamp} {section["crn"]}')

    db_ref.set({
        'title': section['course'],
        'timestamp': timestamp,
        'crn': section['crn'],
        'message': f'Seats {get_keyword(prev, section["seats"]["remaining"])[1]}',
        'origSeats': prev,
        'newSeats': section['seats']['remaining']
    })


def get_keyword(prev, curr):
    if prev <= 0 < curr:
        keyword = "✅", "opened"
    elif prev > 1 and curr <= 0:
        keyword = "❌", "closed"
    elif prev > curr:
        keyword = "📉", "decreased"
    elif prev < curr:
        keyword = "📈", "increased"
    else:
        keyword = "‼️", "changed"

    return keyword


def send_message(to, section, prev):
    curr = section["seats"]["remaining"]
    keyword = get_keyword(prev, curr)

    message = client.messages.create(
        from_=PHONE_NUMBER,
        body=f'{keyword[0]} {section["course"]} - {section["crn"]} - {section["professor"].strip()} has {keyword[1]}!\n{prev} → {curr}',
        to=to
    )

    return message.sid


def send_discord(webhook, embed):
    post_request = requests.post(webhook, json=embed)
    status_code = post_request.status_code

    return status_code




