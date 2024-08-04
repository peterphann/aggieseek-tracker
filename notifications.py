import requests
from twilio.rest import Client
import os
from dotenv import load_dotenv
import logging

load_dotenv()
ACCOUNT_SID = os.getenv('ACCOUNT_SID')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
client = Client(ACCOUNT_SID, AUTH_TOKEN)


def send_message(to, section, prev):
    curr = section["seats"]["remaining"]

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

