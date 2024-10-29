import requests
from firebase_admin import db
from twilio.rest import Client
import os
import embed
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
ACCOUNT_SID = os.getenv(
    'ACCOUNT_SID')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
client = Client(ACCOUNT_SID, AUTH_TOKEN)


def generate_notification(uid, section, prev):
    timestamp = datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%SZ')
    db_ref = db.reference(f'users/{uid}/notifications/{timestamp} {section["CRN"]}')

    db_ref.set({
        'title': section['SUBJECT_CODE'] + " " + section['COURSE_NUMBER'],
        'timestamp': timestamp,
        'crn': section['CRN'],
        'message': f'Seats {get_keyword(prev, section["SEATS"]["REMAINING"])[1]}',
        'origSeats': prev,
        'newSeats': section['SEATS']['REMAINING']
    })


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


def send_message(to, section, prev):
    curr = section["SEATS"]["REMAINING"]
    full_name = section['SUBJECT_CODE'] + " " + section['COURSE_NUMBER']
    emoji, keyword = get_keyword(prev, curr)

    message = client.messages.create(
        from_=PHONE_NUMBER,
        body=f'{emoji} {full_name} - {section["CRN"]} - {section["INSTRUCTOR"].strip()} has {keyword}!\n{prev} → {curr}',
        to=to
    )

    return message.sid


def send_discord(webhook, alert_embed):
    post_request = requests.post(webhook, json=alert_embed)
    status_code = post_request.status_code

    return status_code
