from bs4 import BeautifulSoup
import aiohttp
import logging
import json

# GPT written helper
def recursive_parse_json(json_str):
    try:
        # Try parsing the string as JSON
        parsed = json.loads(json_str)
        
        # If it's a dictionary, recursively parse its values
        if isinstance(parsed, dict):
            return {k: recursive_parse_json(v) for k, v in parsed.items()}
        # If it's a list, recursively parse each element
        elif isinstance(parsed, list):
            return [recursive_parse_json(element) for element in parsed]
        else:
            return parsed
    except (json.JSONDecodeError, TypeError):
        # If parsing fails, return the original string
        return json_str

def parse_soup(soup: BeautifulSoup) -> dict:
    all_fields = soup.find_all('td', class_='dddefault')

    if len(all_fields) == 0:
        return {}

    return {
        'SEATS': {
            'ACTUAL': int(all_fields[2].text),
            'CAPACITY': int(all_fields[1].text),
            'REMAINING': int(all_fields[3].text)
        },
    }

async def get_section_info(term, crn):
    result = {}
    instructor = 'Not assigned'

    async with aiohttp.ClientSession() as session:
        howdy_url = f'https://howdy.tamu.edu/api/course-section-details?term={term}&subject=&course=&crn={crn}'
        compass_url = f'https://compass-ssb.tamu.edu/pls/PROD/bwykschd.p_disp_detail_sched?term_in={term}&crn_in={crn}'
        instructor_url = 'https://howdy.tamu.edu/api/section-meeting-times-with-profs'

        async with session.get(howdy_url) as response:
            if response.status != 200:
                logging.warning(f'Could not fetch CRN {crn} from Howdy.')
                return {}

            result = await response.json()

            if not result:
                logging.warning(f'Could not fetch CRN {crn} from Howdy.')
                return {}
            
        async with session.post(instructor_url, json={"term": term, "subject": None, "course": None, "crn": crn}) as response:
            instructor_result = await response.json()
            if instructor_result and instructor_result.get('SWV_CLASS_SEARCH_INSTRCTR_JSON', None):
                unparsed_json = instructor_result['SWV_CLASS_SEARCH_INSTRCTR_JSON']
                parsed_json = recursive_parse_json(unparsed_json)[0]
                instructor = parsed_json['NAME'].rstrip('(P)')
        
        async with session.get(compass_url) as response:
            try:
                soup = BeautifulSoup(await response.text(), 'html.parser')
                seats = parse_soup(soup)

                result.update(seats)
            except Exception as e:
                logging.error(f'Error while parsing CRN {crn} from Compass.')
                return {}

        result.update({'INSTRUCTOR': instructor})
        return result