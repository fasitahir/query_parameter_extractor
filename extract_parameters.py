import spacy
from rapidfuzz import process
from datetime import datetime, timedelta
import parsedatetime
from autocorrect import Speller
import re

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")
spell = Speller(lang='en')

# City to IATA mapping
city_to_iata = {
    "lahore": "LHE",
    "karachi": "KHI",
    "islamabad": "ISB",
    "rawalpindi": "ISB",   # shares ISB airport
    "multan": "MUX",
    "peshawar": "PEW",
    "quetta": "UET",
    "faisalabad": "LYP",
    "sialkot": "SKT",
    "skardu": "KDU",
    "gilgit": "GIL",
    "sukkur": "SKZ",
    "gwadar": "GWD",
    "turbat": "TUK",
    "bahawalpur": "BHV",
    "dera ghazi khan": "DEA",
    "chitral": "CJL",
    "panjgur": "PJG",
    "moenjodaro": "MJD",
    "parachinar": "PAJ",
    "zhob": "PZH",
    "dalbandin": "DBA",
    "muzaffarabad": "MFG",
    "rahim yar khan": "RYK",
    "nawabshah": "WNS"
}

city_names = list(city_to_iata.keys())
# Create reverse mapping for IATA codes
iata_codes = set(city_to_iata.values())

def correct_spelling(text):
    return spell(text)

def extract_cities_multiword(text):
    """Extract multi-word cities first, then single word cities, and IATA codes"""
    text_lower = text.lower()
    found_cities = []
    
    # First, check for IATA codes (3-letter uppercase codes)
    import re
    iata_pattern = r'\b[A-Z]{3}\b'
    iata_matches = re.finditer(iata_pattern, text.upper())
    
    for match in iata_matches:
        iata_code = match.group()
        if iata_code in iata_codes:
            start_pos = match.start()
            words_before = len(text[:start_pos].split())
            found_cities.append((iata_code, words_before, start_pos))
    
    # Also check for city names (don't return early, combine with IATA codes)
    # Sort cities by length (longest first) to match multi-word cities first
    sorted_cities = sorted(city_names, key=len, reverse=True)
    
    for city in sorted_cities:
        if city in text_lower:
            # Find the position of the city in the text
            start_pos = text_lower.find(city)
            if start_pos != -1:
                # Check if it's a whole word match (not part of another word)
                start_char = start_pos == 0 or not text_lower[start_pos - 1].isalnum()
                end_char = (start_pos + len(city) == len(text_lower) or 
                           not text_lower[start_pos + len(city)].isalnum())
                
                if start_char and end_char:
                    iata = city_to_iata[city]
                    # Calculate approximate token position
                    words_before = len(text_lower[:start_pos].split())
                    found_cities.append((iata, words_before, start_pos))
                    # Remove the matched city from text to avoid overlapping matches
                    text_lower = text_lower.replace(city, " " * len(city), 1)
    
    return found_cities

def extract_cities(query):
    query_lower = query.lower()
    doc = nlp(query_lower)
    
    # First try to extract multi-word cities
    found_cities = extract_cities_multiword(query_lower)
    
    # If no multi-word cities found, try entity recognition and fuzzy matching
    if not found_cities:
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC"):
                match, score, _ = process.extractOne(ent.text.lower(), city_names)
                if score > 85:
                    iata = city_to_iata[match]
                    found_cities.append((iata, ent.start, ent.start_char))
    
    # Fallback to token-based fuzzy matching if still no entities found
    if not found_cities:
        tokens = [token.text for token in doc]  # Keep original case for IATA detection
        for i, token in enumerate(tokens):
            # Check if token is an IATA code
            if len(token) == 3 and token.upper() in iata_codes:
                found_cities.append((token.upper(), i, doc[i].idx))
            else:
                # Try fuzzy matching with city names
                match, score, _ = process.extractOne(token.lower(), city_names)
                if score > 90:
                    iata = city_to_iata[match]
                    found_cities.append((iata, i, doc[i].idx))
    
    # Remove duplicates and sort by character position
    seen = set()
    unique_cities = []
    for city, token_idx, char_idx in found_cities:
        if city not in seen:
            seen.add(city)
            unique_cities.append((city, token_idx, char_idx))
    found_cities = sorted(unique_cities, key=lambda x: x[2])  # Sort by character position
    
    # Use improved logic to identify source and destination
    source = destination = None
    
    # Look for directional indicators
    from_indicators = ["from", "leaving", "departing", "starting"]
    to_indicators = ["to", "towards", "going to", "arriving", "destination"]
    
    # Check for explicit directional phrases
    for token in doc:
        if token.text.lower() in from_indicators:
            # Look for cities after "from" indicators
            for city_info in found_cities:
                city_iata, city_token_idx, city_char_idx = city_info
                if city_char_idx > token.idx:  # City appears after the indicator
                    if not source:  # Take the first one found
                        source = city_iata
                        break
        
        elif token.text.lower() in to_indicators or (token.text.lower() == "to" and token.dep_ == "prep"):
            # Look for cities after "to" indicators
            for city_info in found_cities:
                city_iata, city_token_idx, city_char_idx = city_info
                if city_char_idx > token.idx:  # City appears after the indicator
                    if not destination:  # Take the first one found
                        destination = city_iata
                        break
    
    # Fallback: If no clear indicators found, use position-based logic
    if not source and not destination and found_cities:
        if len(found_cities) == 1:
            # Single city - could be either source or destination
            # Check context for clues
            if any(word in query_lower for word in to_indicators + ["going", "want to go"]):
                destination = found_cities[0][0]
            else:
                source = found_cities[0][0]
        else:
            # Multiple cities - first is typically source, second is destination
            source = found_cities[0][0]
            destination = found_cities[1][0]
    
    # Handle cases where we have indicators but cities were assigned to wrong slots
    if source and not destination and len(found_cities) > 1:
        # If we have a source but no destination, and there are multiple cities
        for city_info in found_cities:
            if city_info[0] != source:
                destination = city_info[0]
                break
    
    elif destination and not source and len(found_cities) > 1:
        # If we have a destination but no source, and there are multiple cities
        for city_info in found_cities:
            if city_info[0] != destination:
                source = city_info[0]
                break
    
    # Ensure source != destination
    if source == destination:
        if len(found_cities) > 1:
            # If they're the same, reassign based on position
            source = found_cities[0][0]
            destination = found_cities[1][0]
        else:
            destination = None
    
    return source, destination

def extract_date(text):
    text = correct_spelling(text.lower())
    today = datetime.now()

    if "day after tomorrow" in text:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")
    elif "tomorrow" in text:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    elif "today" in text:
        return today.strftime("%Y-%m-%d")

    # Fix for "5th of December" pattern - replace "of" with space
    text = re.sub(r'(\d+)(st|nd|rd|th)\s+of\s+', r'\1\2 ', text)
    
    cal = parsedatetime.Calendar()
    time_struct, parse_status = cal.parse(text)
    if parse_status == 1:
        parsed_date = datetime(*time_struct[:6])
        return parsed_date.strftime("%Y-%m-%d")

    return None

def extract_travel_info(query):
    result = {}
    source, destination = extract_cities(query)

    if source and destination and source == destination:
        # Discard invalid pair
        destination = None

    if source:
        result["source"] = source
    if destination:
        result["destination"] = destination

    date = extract_date(query)
    if date:
        result["date"] = date

    return result

# Command-line interface
if __name__ == "__main__":
    while True:
        query = input("Enter your travel query: ")
        if query.strip().lower() in ["exit", "quit"]:
            break
        print(extract_travel_info(query))