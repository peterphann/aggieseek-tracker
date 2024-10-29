from typing import Dict

# Default icons for discord embed
TAMU_LOGO = 'https://i.imgur.com/qHXokad.jpeg'
COURSE_LOGO = 'https://i.imgur.com/YZrjP8O.png'
AGGIESEEK_LOGO_LARGE = 'https://i.imgur.com/JKumwkg.png'
AGGIESEEK_LOGO = 'https://i.imgur.com/IGwnRFi.png'
COURSE_COLOR = 0x09adef
INCREASE_EMOJI = '<:yes:1171343018880667669>'
NO_CHANGE_EMOJI = '<:maybe:1171343019665014805>'
DECREASE_EMOJI = '<:no:1171343016980643872>'

def parse_title(section: Dict, title: str) -> str:
    title = title.replace('%t', section['COURSE_TITLE'])
    title = title.replace('%c', str(section['CRN']))
    title = title.replace('%C', section['SUBJECT_CODE'] + " " + section['COURSE_NUMBER'])
    title = title.replace('%S', str(section['SECTION_NUMBER']))
    title = title.replace('%p', section['INSTRUCTOR'])

    return title


def console_embed(logs) -> dict:
    logs_joined = '\n'.join(logs)
    return {
        "avatar_url": AGGIESEEK_LOGO,
        "username": "AggieSeek",
        "content": f'```{logs_joined}```'
    }

def update_embed(section, prev) -> dict:
    curr = section['SEATS']['REMAINING']
    change_symbol = INCREASE_EMOJI if curr > prev else DECREASE_EMOJI if curr < prev else NO_CHANGE_EMOJI
    title = parse_title(section, '%C - %c - %p')

    return {
        "avatar_url": AGGIESEEK_LOGO_LARGE,
        "username": "AggieSeek",
        "embeds": [{
            "author": {
                "name": 'AggieSeek',
                "icon_url": AGGIESEEK_LOGO
            },
            "color": COURSE_COLOR,
            "title": title,
            "description": f'{change_symbol} **CHANGE DETECTED** {change_symbol}',
            "fields": [
                {
                    "name": "Previous",
                    "value": prev,
                    "inline": True
                },
                {
                    "name": "Current",
                    "value": curr,
                    "inline": True
                }
            ],
            "thumbnail": {
                "url": AGGIESEEK_LOGO_LARGE
            }
        }]
    }