# Default icons for discord embed
TAMU_LOGO = 'https://i.imgur.com/qHXokad.jpeg'
COURSE_LOGO = 'https://i.imgur.com/YZrjP8O.png'
AGGIESEEK_LOGO = 'https://i.imgur.com/DzvtyJ0.png'
COURSE_COLOR = 0x09adef
INCREASE_EMOJI = '<:yes:1171343018880667669>'
NO_CHANGE_EMOJI = '<:maybe:1171343019665014805>'
DECREASE_EMOJI = '<:no:1171343016980643872>'


def parse_title(section: {}, title: str) -> str:

    title = title.replace('%t', section['title'])
    title = title.replace('%c', str(section['crn']))
    title = title.replace('%C', section['course'])
    title = title.replace('%S', str(section['section']))
    title = title.replace('%p', section['professor'])

    return title


def update_embed(section, prev) -> dict:
    course_link = f'https://tamu.collegescheduler.com/terms/{"%20".join(section["term"].split(" "))}%20-%20College%20Station/currentschedule'
    curr = section['seats']['remaining']
    change_symbol = INCREASE_EMOJI if curr > prev else DECREASE_EMOJI if curr < prev else NO_CHANGE_EMOJI
    title = parse_title(section, '%C - %c - %p')

    return {
        "avatar_url": TAMU_LOGO,
        "username": "Texas A&M University",
        "embeds": [{
            "author": {
                "name": 'AggieSeek',
                "url": course_link,
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
                "url": TAMU_LOGO
            }
        }]
    }