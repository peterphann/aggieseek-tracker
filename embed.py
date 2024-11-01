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

def generate_link(term_code):
    semesters = ['Spring', 'Summer', 'Fall', 'Full Yr Professional']
    locations = ['College Station', 'Galveston', 'Qatar', '', 'Half Year Term']

    term_code = str(term_code)
    year = int(term_code[:4])
    semester = semesters[int(term_code[4]) - 1]
    location = locations[int(term_code[5]) - 1]
    
    if int(term_code[4]) == 4:
        term_string = f'{semester} {year}-{year + 1}'
    else:
        term_string = f'{semester} {year} - {location}'
    return f'https://tamu.collegescheduler.com/terms/{term_string}/options'

def format_title(section: Dict, title: str) -> str:
    title = title.replace('%t', section['COURSE_TITLE'])
    title = title.replace('%c', str(section['CRN']))
    title = title.replace('%C', section['SUBJECT_CODE'] + " " + section['COURSE_NUMBER'])
    title = title.replace('%S', str(section['SECTION_NUMBER']))
    title = title.replace('%p', section['INSTRUCTOR'])

    return title

def instructor_embed(section, previous, current) -> dict:
    title = format_title(section, '%C - %c - %p')

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
            "description": '**INSTRUCTOR CHANGED**',
            "fields": [
                {
                    "name": "Previous",
                    "value": previous,
                    "inline": True
                },
                {
                    "name": "Current",
                    "value": current,
                    "inline": True
                }
            ],
            "thumbnail": {
                "url": AGGIESEEK_LOGO_LARGE
            }
        }]
    }

def seats_embed(section, previous, current) -> dict:
    change_symbol = INCREASE_EMOJI if current > previous else DECREASE_EMOJI if current < previous else NO_CHANGE_EMOJI
    title = format_title(section, '%C - %c - %p')

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
            "description": f'{change_symbol} **SEATS CHANGED** {change_symbol}',
            "fields": [
                {
                    "name": "Previous",
                    "value": previous,
                    "inline": True
                },
                {
                    "name": "Current",
                    "value": current,
                    "inline": True
                }
            ],
            "thumbnail": {
                "url": AGGIESEEK_LOGO_LARGE
            }
        }]
    }