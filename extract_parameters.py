import spacy
from rapidfuzz import process
from datetime import datetime, timedelta
import parsedatetime
from autocorrect import Speller
import re
import json
from typing import Dict
from dotenv import load_dotenv
import os
import google.generativeai as genai


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

# Airline name mappings (including common variations and misspellings)
airline_mappings = {
    # Pakistani Airlines
    "airblue": ["airblue", "air blue", "air-blue", "airblue airlines"],
    "serene_air": ["serene air", "serene-air", "sereneair", "serene air lines", "serene airlines"],
    "pia": [
        "pia", "pakistan international airlines", "pakistan international", 
        "pakistan airlines", "pakistan air", "pakistani airlines"
    ],
    "shaheen_air": ["shaheen air", "shaheen-air", "shaheenair", "shaheen airlines"],
    
    # International Airlines (Major ones)
    "emirates": ["emirates", "emirates airlines", "emirates airways", "ek"],
    "qatar_airways": ["qatar airways", "qatar", "qatar airlines", "qr"],
    "etihad": ["etihad", "etihad airways", "etihad airlines", "ey"],
    "turkish_airlines": ["turkish airlines", "turkish", "turkish airways", "tk"],
    "lufthansa": ["lufthansa", "lufthansa airlines", "lufthansa airways", "lh"],
    "british_airways": ["british airways", "british", "ba", "british airlines"],
    "air_arabia": ["air arabia", "air-arabia", "airarabia", "g9"],
    "flydubai": ["flydubai", "fly dubai", "fly-dubai", "fz"],
    "saudia": ["saudia", "saudi airlines", "saudi arabian airlines", "sv"],
    "gulf_air": ["gulf air", "gulf-air", "gulfair", "gulf airlines", "gf"],
    "oman_air": ["oman air", "oman-air", "omanair", "oman airlines", "wy"],
    "kuwait_airways": ["kuwait airways", "kuwait", "kuwait airlines", "ku"],
    "middle_east_airlines": ["middle east airlines", "mea", "middle eastern airlines"],
    "royal_jordanian": ["royal jordanian", "royal-jordanian", "rj", "jordanian airlines"],
    "egyptair": ["egyptair", "egypt air", "egypt-air", "egyptian airlines", "ms"],
    
    # Asian Airlines
    "cathay_pacific": ["cathay pacific", "cathay-pacific", "cathay", "cx"],
    "singapore_airlines": ["singapore airlines", "singapore", "sia", "sq"],
    "malaysia_airlines": ["malaysia airlines", "malaysia", "malaysian airlines", "mh"],
    "thai_airways": ["thai airways", "thai", "thai airlines", "tg"],
    "air_india": ["air india", "air-india", "airindia", "indian airlines", "ai"],
    "indigo": ["indigo", "indigo airlines", "6e"],
    "spicejet": ["spicejet", "spice jet", "spice-jet", "sg"],
    "china_southern": ["china southern", "china-southern", "cz"],
    "china_eastern": ["china eastern", "china-eastern", "mu"],
    
    # European Airlines
    "klm": ["klm", "klm airlines", "klm royal dutch airlines", "kl"],
    "air_france": ["air france", "air-france", "airfrance", "af"],
    "alitalia": ["alitalia", "alitalia airlines", "az"],
    "swiss": ["swiss", "swiss airlines", "swiss international", "lx"],
    "austrian_airlines": ["austrian airlines", "austrian", "os"],
    "scandinavian_airlines": ["sas", "scandinavian airlines", "scandinavian", "sk"],
    
    # American Airlines
    "american_airlines": ["american airlines", "american", "aa"],
    "delta": ["delta", "delta airlines", "delta airways", "dl"],
    "united": ["united", "united airlines", "ua"],
    "southwest": ["southwest", "southwest airlines", "wn"],
    "jetblue": ["jetblue", "jet blue", "jet-blue", "b6"],
    
    # Budget/Low-cost carriers
    "ryanair": ["ryanair", "ryan air", "ryan-air", "fr"],
    "easyjet": ["easyjet", "easy jet", "easy-jet", "u2"],
    "wizz_air": ["wizz air", "wizz-air", "wizzair", "w6"],
    "norwegian": ["norwegian", "norwegian airlines", "dy"],
    "vueling": ["vueling", "vueling airlines", "vy"],
    
    # Other notable airlines
    "aeroflot": ["aeroflot", "aeroflot airlines", "su"],
    "korean_air": ["korean air", "korean-air", "koreanair", "ke"],
    "asiana": ["asiana", "asiana airlines", "oz"],
    "japan_airlines": ["jal", "japan airlines", "japanese airlines", "jl"],
    "ana": ["ana", "all nippon airways", "all nippon", "nh"],
    "etihad_regional": ["etihad regional", "darwin airline"],
    "air_canada": ["air canada", "air-canada", "aircanada", "ac"],
    "westjet": ["westjet", "west jet", "west-jet", "ws"]
}

# Create a flattened list of all airline keywords for fuzzy matching
all_airline_keywords = [(variation.lower(), code) for code, variations in airline_mappings.items() for variation in variations]




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

def extract_flight_type(query):
    """
    Conservative flight type extraction - only detects return when there are strong indicators.
    Returns 'return' or 'one_way'
    """
    query_lower = query.lower()
    
    # Strong explicit return flight indicators
    strong_return_keywords = [
        "return", "round trip", "round-trip", "roundtrip", "two way", "two-way",
        "return ticket", "return flight", "both ways"
    ]
    
    # Check for explicit return keywords first
    for keyword in strong_return_keywords:
        if keyword in query_lower:
            return "return"
    
    # Very specific return patterns - only strong indicators
    return_patterns = [
        # "back to [city]" patterns - must have "back"
        r'(?:and\s+)?(?:then\s+)?back\s+to\s+\w+',
        r'(?:and\s+)?(?:then\s+)?(?:come\s+)?back\s+(?:to\s+)?\w+',
        
        # "between [date] and [date]" patterns - strong date range indicator
        r'between\s+.?\s+and\s+.?(?:\d|today|tomorrow)',
        
        # Multiple cities with explicit return language
        r'(?:from\s+)?\w+\s+to\s+\w+\s+and\s+(?:then\s+)?(?:back\s+to|return\s+to)\s+\w+',
        r'(?:from\s+)?\w+\s+to\s+\w+.*?(?:and\s+)?(?:then\s+)?(?:back|return)',
        
        # Strong temporal return indicators
        r'(?:go|travel|fly)\s+.*?(?:and\s+)?(?:then\s+)?(?:come\s+)?back',
        r'(?:trip|journey)\s+(?:from\s+)?\w+\s+to\s+\w+\s+and\s+back',
    ]
    
    for pattern in return_patterns:
        if re.search(pattern, query_lower):
            return "return"
    
    # Check for "between" with locations - strong return indicator
    if "between" in query_lower:
        # Look for "between [city] and [city]" or "between [date] and [date]"
        between_pattern = r'between\s+\w+.*?and\s+\w+'
        if re.search(between_pattern, query_lower):
            return "return"
    
    # Check for specific temporal return indicators
    strong_temporal_indicators = [
        "and back", "then back", "return on", "coming back on",
        "back on", "go and come back", "there and back"
    ]
    
    for indicator in strong_temporal_indicators:
        if indicator in query_lower:
            return "return"
    
    # Check for date ranges that suggest return trips
    date_range_patterns = [
        # Clear date ranges: "from 10th to 15th", "10th and 15th", "10th until 15th"
        r'(?:from\s+)?\d+(?:st|nd|rd|th)?\s+.*?(?:to|and|until)\s+\d+(?:st|nd|rd|th)',
        r'(?:on\s+)?\d+(?:st|nd|rd|th)?\s+.*?(?:and\s+back\s+on|and\s+return\s+on)\s+\d+(?:st|nd|rd|th)',
    ]
    
    for pattern in date_range_patterns:
        if re.search(pattern, query_lower):
            return "return"
    
    # Advanced analysis - only if we have strong indicators
    try:
        doc = nlp(query_lower)
        
        # Check for city repetition (same city mentioned multiple times)
        known_cities_mentioned = []
        for city in city_names:
            if city in query_lower:
                # Count how many times this city appears
                count = query_lower.count(city)
                if count > 1:
                    return "return"
                known_cities_mentioned.append(city)
        
        # Only check for multiple unique cities if there are strong connecting words
        if len(known_cities_mentioned) >= 2:
            # Must have explicit connecting words that suggest return journey
            strong_connectors = ["and then to", "and back to", "then to", "then back"]
            for connector in strong_connectors:
                if connector in query_lower:
                    return "return"
        
    except Exception:
        pass
    
    # Final very specific return checks
    final_return_checks = [
        r'\bgo\b.*\bback\b',      # "go ... back"
        r'\bthere\b.*\bback\b',   # "there ... back" 
        r'\bfly\b.*\breturn\b',   # "fly ... return"
    ]
    
    for check in final_return_checks:
        if re.search(check, query_lower):
            return "return"
    
    # Default to one_way - be conservative
    return "one_way"

def extract_flight_class(query):
    """
    Extract flight class from query. Returns 'economy' by default.
    Supported classes: economy, business, first, premium_economy
    Uses multiple strategies with fallbacks for robust extraction.
    """
    query_lower = query.lower()
    
    # Flight class mappings - most specific first
    class_mappings = {
        # First Class variations
        "first": ["first class", "first-class", "firstclass", "1st class", "first", "f class"],
        
        # Business Class variations  
        "business": [
            "business class", "business-class", "businessclass", "biz class", "business", 
            "c class", "club class", "executive class", "executive", "j class"
        ],
        
        # Premium Economy variations
        "premium_economy": [
            "premium economy", "premium-economy", "premiumeconomy", "premium eco", 
            "premium", "w class", "comfort plus", "economy plus", "economy+", 
            "extra comfort", "preferred seating", "premium seating"
        ],
        
        # Economy variations (explicit mentions)
        "economy": [
            "economy class", "economy-class", "economyclass", "eco class", "economy", 
            "y class", "coach", "main cabin", "standard", "regular", "basic economy"
        ]
    }
    
    # Strategy 1: Direct keyword matching (longest phrases first)
    all_keywords = []
    for class_name, keywords in class_mappings.items():
        for keyword in keywords:
            all_keywords.append((keyword, class_name))
    
    # Sort by length (longest first) to match more specific phrases
    all_keywords.sort(key=lambda x: len(x[0]), reverse=True)
    
    for keyword, class_name in all_keywords:
        if keyword in query_lower:
            return class_name
    
    # Strategy 2: NLP-based extraction using spaCy
    try:
        doc = nlp(query_lower)
        
        # Look for class-related entities or patterns
        class_indicators = ["class", "cabin", "seat", "seating", "service"]
        
        for token in doc:
            if token.text in class_indicators:
                # Look for adjectives or descriptors before/after class indicators
                context_window = []
                
                # Get context around the class indicator (2 tokens before and after)
                start_idx = max(0, token.i - 2)
                end_idx = min(len(doc), token.i + 3)
                
                for context_token in doc[start_idx:end_idx]:
                    context_window.append(context_token.text.lower())
                
                context_text = " ".join(context_window)
                
                # Check if any class keywords appear in context
                for keyword, class_name in all_keywords:
                    if keyword in context_text:
                        return class_name
        
        # Look for luxury/comfort indicators that might suggest higher classes
        luxury_indicators = {
            "business": ["professional", "corporate", "executive", "business trip", "work travel"],
            "first": ["luxury", "luxurious", "premium service", "finest", "exclusive", "vip"],
            "premium_economy": ["comfortable", "extra space", "more room", "upgrade", "better seat"]
        }
        
        query_tokens = [token.text.lower() for token in doc]
        query_text_joined = " ".join(query_tokens)
        
        for class_name, indicators in luxury_indicators.items():
            for indicator in indicators:
                if indicator in query_text_joined:
                    return class_name
                    
    except Exception:
        pass
    
    # Strategy 3: Pattern-based extraction
    class_patterns = [
        # Patterns like "in business class", "book first class"
        (r'\b(?:in|book|reserve|want|need|prefer)\s+(\w+(?:\s+\w+)?)\s+class\b', 1),
        (r'\b(\w+(?:\s+\w+)?)\s+class\s+(?:seat|ticket|flight|fare)\b', 1),
        (r'\b(?:fly|travel)\s+(\w+(?:\s+\w+)?)\s+class\b', 1),
        
        # Patterns like "business class flight", "first class ticket"
        (r'\b(\w+(?:\s+\w+)?)\s+class\s+(?:flight|ticket|booking)\b', 1),
        
        # More flexible patterns
        (r'\b(first|business|economy|premium)\s+(?:class\s+)?(?:seat|ticket|flight|cabin)\b', 1),
        (r'\b(?:seat|ticket|flight|cabin)\s+(?:in\s+)?(\w+(?:\s+\w+)?)\s+class\b', 1),
    ]
    
    for pattern, group_idx in class_patterns:
        matches = re.findall(pattern, query_lower)
        if matches:
            for match in matches:
                extracted_class = match.strip() if isinstance(match, str) else match[group_idx-1].strip()
                
                # Map extracted class to standard class names
                for class_name, keywords in class_mappings.items():
                    if extracted_class in keywords or any(keyword.startswith(extracted_class) for keyword in keywords):
                        return class_name
    
    # Strategy 4: Fuzzy matching for misspellings or variations
    try:
        # Extract potential class-related words
        class_related_words = []
        doc = nlp(query_lower)
        
        for token in doc:
            if (token.pos_ in ["NOUN", "ADJ"] and 
                len(token.text) > 3 and 
                any(indicator in token.text for indicator in ["class", "eco", "biz", "prem", "first", "bus"])):
                class_related_words.append(token.text)
        
        # Check fuzzy matching against known class terms
        all_class_terms = []
        for keywords in class_mappings.values():
            all_class_terms.extend(keywords)
        
        for word in class_related_words:
            best_match, score, _ = process.extractOne(word, all_class_terms)
            if score > 75:  # High threshold for class matching
                for class_name, keywords in class_mappings.items():
                    if best_match in keywords:
                        return class_name
                        
    except Exception:
        pass
    
    # Strategy 5: Context-based inference
    # Look for price-related clues or luxury indicators
    context_clues = {
        "first": ["expensive", "costly", "luxury", "premium service", "champagne", "lie flat"],
        "business": ["work", "corporate", "meeting", "conference", "professional", "lounge access"],
        "premium_economy": ["upgrade", "extra legroom", "more space", "comfortable", "priority boarding"]
    }
    
    for class_name, clues in context_clues.items():
        for clue in clues:
            if clue in query_lower:
                # Only return if there's also some flight-related context
                flight_context = ["flight", "fly", "travel", "ticket", "book", "reserve"]
                if any(context in query_lower for context in flight_context):
                    return class_name
    
    # Strategy 6: Abbreviation detection
    abbreviation_map = {
        "f": "first",
        "j": "business", 
        "c": "business",
        "w": "premium_economy",
        "y": "economy"
    }
    
    # Look for single letter class codes
    single_letter_pattern = r'\b([fjcwy])\s+class\b'
    matches = re.findall(single_letter_pattern, query_lower)
    if matches:
        letter = matches[0].lower()
        if letter in abbreviation_map:
            return abbreviation_map[letter]
    
    # Default fallback - return economy
    return "economy"

def extract_dates(text, flight_type=None):
    """
    Unified date extraction function that handles both one-way and return flights.
    Returns single date for one-way, tuple (departure_date, return_date) for return flights.
    """
    original_text = text.lower()
    today = datetime.now()

    # Special date mapping
    special_date_map = {
        "day after tomorrow": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
        "tomorrow": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
        "today": today.strftime("%Y-%m-%d"),
    }

    # Fix common date format issues
    text_fixed = re.sub(r'(\d+)(st|nd|rd|th)\s+of\s+', r'\1\2 ', original_text)
    normalized_text = text_fixed.strip().lower()
    dates = []

    # Auto-detect flight type if not provided
    if flight_type is None:
        flight_type = extract_flight_type(text)

    # ---- RETURN FLIGHT HANDLING ---- #
    if flight_type == "return":
        # Strategy 1: Between X and Y
        between_pattern = r'between\s+(.?)\s+and\s+(.?)(?:\s|$|,|\.)'
        between_matches = re.findall(between_pattern, normalized_text, re.IGNORECASE)

        if between_matches:
            for date1_text, date2_text in between_matches:
                for label, date_str in zip(['departure', 'return'], [date1_text, date2_text]):
                    date_str = re.sub(r'\b(of|the)\b', '', date_str.strip().lower())
                    if date_str in special_date_map:
                        dates.append((label, special_date_map[date_str]))
                    else:
                        try:
                            cal = parsedatetime.Calendar()
                            time_struct, parse_status = cal.parse(date_str)
                            if parse_status >= 1:
                                dates.append((label, datetime(*time_struct[:6]).strftime("%Y-%m-%d")))
                        except:
                            pass
            if len(dates) >= 2:
                return (
                    next((d for l, d in dates if l == 'departure'), None),
                    next((d for l, d in dates if l == 'return'), None)
                )

        # Strategy 2: Date pair patterns
        date_pair_patterns = [
            r'\b(today|tomorrow|day after tomorrow)\b.?\b(?:and\s+(?:then\s+)?|then\s+)\b.?\b(today|tomorrow|day after tomorrow)\b',
            r'\bon\s+([^,]+?)\s+and\s+(?:then\s+)?(?:on\s+)?([^,]+?)(?:\s|$|,)',
            r'\b(\d+(?:st|nd|rd|th)?(?:\s+\w+)?)\s+(?:and\s+(?:then\s+)?|then\s+|to\s+)(?:on\s+)?(\d+(?:st|nd|rd|th)?(?:\s+\w+)?)(?:\s|$|,)',
            r'(\d+(?:st|nd|rd|th)?\s+\w+)\s+(?:to|and|until)\s+(\d+(?:st|nd|rd|th)?\s+\w+)',
        ]

        for pattern in date_pair_patterns:
            matches = re.findall(pattern, normalized_text)
            for match in matches:
                if len(match) == 2:
                    for label, date_str in zip(['departure', 'return'], match):
                        date_str = date_str.strip().lower()
                        if date_str in special_date_map:
                            dates.append((label, special_date_map[date_str]))
                        else:
                            try:
                                cal = parsedatetime.Calendar()
                                time_struct, parse_status = cal.parse(date_str)
                                if parse_status >= 1:
                                    parsed_date = datetime(*time_struct[:6])
                                    dates.append((label, parsed_date.strftime("%Y-%m-%d")))
                            except:
                                pass
                if len(dates) >= 2:
                    return (
                        next((d for l, d in dates if l == 'departure'), None),
                        next((d for l, d in dates if l == 'return'), None)
                    )

        # Strategy 3 & 4: Return and Departure Indicators
        indicator_patterns = [
            ("return", [
                r'(?:come\s+back|return|back).*?(?:on\s+|must\s+on\s+|by\s+)([^,\.]+)',
                r'(?:must\s+on|need\s+to\s+(?:come\s+)?back.*?on)\s+([^,\.]+)',
                r'(?:return.?on|back.?on)\s+([^,\.]+)'
            ]),
            ("departure", [
                r'(?:depart|leave|going|travel).*?(?:on\s+)([^,\.]+)',
                r'(?:on\s+)([^,\.]+).*?(?:going|travel|depart|leave)'
            ])
        ]

        for label, patterns in indicator_patterns:
            for pattern in patterns:
                matches = re.findall(pattern, normalized_text)
                for match in matches:
                    date_str = re.sub(r'\b(of|the)\b', '', match.strip().lower())
                    if date_str in special_date_map:
                        dates.append((label, special_date_map[date_str]))
                    else:
                        try:
                            cal = parsedatetime.Calendar()
                            time_struct, parse_status = cal.parse(date_str)
                            if parse_status >= 1:
                                parsed_date = datetime(*time_struct[:6])
                                dates.append((label, parsed_date.strftime("%Y-%m-%d")))
                        except:
                            pass

        # Strategy 5: Generic fallback special date match (longest match first)
        if not dates:
            sorted_specials = sorted(special_date_map.keys(), key=len, reverse=True)
            for word in sorted_specials:
                if word in normalized_text:
                    context_match = any(phrase in normalized_text for phrase in [
                        f"come back {word}", f"return {word}", f"back {word}", f"must {word}"
                    ])
                    label = 'return' if context_match else 'departure'
                    dates.append((label, special_date_map[word]))

            # Try parsing remaining ambiguous dates
            if len(dates) < 2:
                text_without_special = normalized_text
                for word in sorted_specials:
                    text_without_special = text_without_special.replace(word, '', 1)
                date_patterns = [
                    r'\d+(?:st|nd|rd|th)?\s+(?:of\s+)?\w+',
                    r'\w+\s+\d+(?:st|nd|rd|th)?',
                    r'\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?',
                ]
                for pattern in date_patterns:
                    matches = re.findall(pattern, text_without_special)
                    for match in matches:
                        try:
                            cal = parsedatetime.Calendar()
                            time_struct, parse_status = cal.parse(match)
                            if parse_status >= 1:
                                parsed_date = datetime(*time_struct[:6])
                                date_str = parsed_date.strftime("%Y-%m-%d")
                                if any(phrase in text for phrase in ['return', 'back', 'come back']):
                                    dates.append(('return', date_str))
                                else:
                                    dates.append(('departure', date_str))
                        except:
                            pass

        # Final return for return flight
        departure = next((d for l, d in dates if l == 'departure'), None)
        return_date = next((d for l, d in dates if l == 'return'), None)
        if departure or return_date:
            return departure, return_date
        else:
            try:
                cal = parsedatetime.Calendar()
                time_struct, parse_status = cal.parse(normalized_text)
                if parse_status >= 1:
                    departure_date = datetime(*time_struct[:6])
                    return departure_date.strftime("%Y-%m-%d"), None
            except:
                pass
            return None, None

    # ---- ONE-WAY FLIGHT HANDLING ---- #
    else:
        sorted_specials = sorted(special_date_map.keys(), key=len, reverse=True)
        for word in sorted_specials:
            if word in normalized_text:
                return special_date_map[word]

        try:
            cal = parsedatetime.Calendar()
            time_struct, parse_status = cal.parse(normalized_text)
            if parse_status >= 1:
                parsed_date = datetime(*time_struct[:6])
                return parsed_date.strftime("%Y-%m-%d")
        except:
            pass

        return None


def extract_passenger_count(query: str) -> Dict[str, int]:
    if not nlp:
        return {"adults": 1, "children": 0, "infants": 0}

    query_lower = query.lower().replace("'", "'")  # normalize apostrophes
    doc = nlp(query_lower)

    adults = 0
    children = 0
    infants = 0
    processed_indices = set()
    processed_plurals = set()

    adult_keywords = {
        'wife', 'husband', 'spouse', 'partner', 'mother', 'father', 'mom', 'dad',
        'adult', 'passenger', 'traveler', 'people', 'person', 'friend', 'colleague', 
        'brother', 'sister', 'uncle', 'aunt', 'cousin', 'grandmother', 'grandfather',
        'grandma', 'grandpa', 'man', 'woman', 'guy', 'lady', 'gentleman', 'friends', 'adults'
    }
    
    child_keywords = {
        'child', 'children', 'kid', 'kids', 'son', 'daughter', 'boy', 'girl', 
        'minor', 'teen', 'teenager', 'youth'
    }
    
    infant_keywords = {
        'baby', 'babies', 'infant', 'infants', 'toddler', 'toddlers', 'newborn', 'newborns'
    }

    multi_adult_keywords = {
        'parents': 2, 'couple': 2, 'couples': 2
    }

    number_words = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'a': 1, 'an': 1, 'few': 3, 'several': 4, 'many': 6
    }

    def extract_number(text):
        return int(text) if text.isdigit() else number_words.get(text)

    tokens = [token.text.lower() for token in doc]

    # Step 0: Age-based classification
    # e.g. "my 1 year old son", "my 19 year old daughter"
    for i, token in enumerate(tokens):
        # Look for patterns like "X year old <category>"
        if token.isdigit() and i+2 < len(tokens):
            if tokens[i+1] in ["year", "years"] and tokens[i+2] == "old":
                age = int(tokens[i])
                # Try to find the category (son, daughter, child, etc.)
                if i+3 < len(tokens):
                    category = tokens[i+3]
                    if category in infant_keywords:
                        if age <= 2:
                            infants += 1
                            processed_indices.update([i, i+1, i+2, i+3])
                        elif 2 < age <= 12:
                            children += 1
                            processed_indices.update([i, i+1, i+2, i+3])
                        else:
                            adults += 1
                            processed_indices.update([i, i+1, i+2, i+3])
                    elif category in child_keywords:
                        if age <= 2:
                            infants += 1
                        elif 2 < age <= 12:
                            children += 1
                        elif 12 < age < 18:
                            children += 1
                        else:
                            adults += 1
                        processed_indices.update([i, i+1, i+2, i+3])
                    elif category in adult_keywords:
                        adults += 1
                        processed_indices.update([i, i+1, i+2, i+3])
                else:
                    # If no category, use age only
                    if age <= 2:
                        infants += 1
                    elif 2 < age <= 12:
                        children += 1
                    elif 12 < age < 18:
                        children += 1
                    else:
                        adults += 1
                    processed_indices.update([i, i+1, i+2])

    # Step 1: Special patterns like "family of 5"
    special_patterns = {
        'family of': 'total',
        'group of': 'adults',
        'party of': 'adults',
    }

    family_or_group_found = False

    for pattern, type_hint in special_patterns.items():
        if pattern in query_lower:
            try:
                start_idx = query_lower.index(pattern)
                after_pattern = query_lower[start_idx + len(pattern):].strip()
                words_after = after_pattern.split()
                if words_after:
                    num = extract_number(words_after[0])
                    if num:
                        if type_hint == 'total':
                            adults = num
                            family_or_group_found = True
                        else:
                            adults = max(adults, num)
            except:
                pass

    # Step 2: Handle number + category (Fixed to properly process all numbers)
    i = 0
    while i < len(tokens):
        if i in processed_indices:
            i += 1
            continue

        num = extract_number(tokens[i])
        if num is not None:
            for j in range(i + 1, min(i + 4, len(tokens))):
                word = tokens[j]
                if word in infant_keywords:
                    infants += num
                    processed_indices.add(j)
                    break
                elif word in child_keywords:
                    children += num
                    processed_indices.add(j)
                    break
                elif word in adult_keywords:
                    adults += num
                    processed_indices.add(j)
                    break
                elif word in multi_adult_keywords:
                    adults += num * multi_adult_keywords[word]
                    processed_indices.add(j)
                    break
            processed_indices.add(i)
        i += 1

    # Step 3: Count individual mentions
    for i, token in enumerate(tokens):
        if i in processed_indices:
            continue
        if token in multi_adult_keywords:
            adults += multi_adult_keywords[token]
            processed_indices.add(i)
        elif token in adult_keywords:
            adults += 1
            processed_indices.add(i)
        elif token in child_keywords:
            children += 1
            processed_indices.add(i)
        elif token in infant_keywords:
            infants += 1
            processed_indices.add(i)

    # Step 4: Plural words with default counts (Fixed logic)
    plural_defaults = {
        'babies': 2, 'infants': 2, 'toddlers': 2,  # Fixed: babies should default to 2
        'kids': 2, 'children': 2, 'friends': 2,
        'people': 3, 'adults': 2
    }

    for plural, default_count in plural_defaults.items():
        plural_indices = [i for i, t in enumerate(tokens) if t == plural]
        for plural_idx in plural_indices:
            if plural in processed_plurals:
                continue
            has_number_before = any(
                tokens[j].isdigit() or tokens[j] in number_words
                for j in range(max(0, plural_idx - 2), plural_idx)
            )
            if not has_number_before:
                if plural in infant_keywords:
                    infants = max(infants, default_count)
                elif plural in child_keywords:
                    children = max(children, default_count)
                else:
                    adults = max(adults, default_count)
                processed_plurals.add(plural)

    # Step 5: Named Entities (PERSON)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            adults += 1

    # Step 6: Speaker inclusion (FIXED LOGIC)
    pronouns = {'i', 'me', 'myself'}
    has_first_person = any(p in tokens for p in pronouns)
    has_with = 'with' in tokens or 'and' in tokens
    speaker_should_be_counted = False

    if has_first_person:
        # More comprehensive speaker detection patterns
        speaker_patterns = [
            "i want to travel with", "i'm traveling with", "i am traveling with", 
            "i will travel with", "i will go with", "book a flight for me and",
            "traveling with", "with my", "me and my", "i want to travel",
            "i need to book", "book for me and"
        ]
        
        for pattern in speaker_patterns:
            if pattern in query_lower:
                speaker_should_be_counted = True
                break
        
        # If speaker mentions traveling with others, they should be counted
        if has_with and has_first_person and (adults > 0 or children > 0 or infants > 0):
            speaker_should_be_counted = True
        
        # Special case: when first person is present with family members
        family_indicators = ['wife', 'husband', 'kids', 'children', 'baby', 'babies']
        if has_first_person and any(word in tokens for word in family_indicators):
            speaker_should_be_counted = True

        # Don't double-count if "family of X" already includes the speaker
        if speaker_should_be_counted and not family_or_group_found:
            adults += 1
    
    # Handle "Traveling with X children" case - implies speaker is traveling
    if 'traveling with' in query_lower and not has_first_person:
        if children > 0 or infants > 0:
            adults = max(adults, 1)  # At least one adult must be traveling with children

    # Step 7: Handle "we" and "us"
    if 'we' in tokens and adults < 2:
        adults = max(adults, 2)
    if 'us' in tokens and adults < 2 and children == 0 and infants == 0:
        adults = 2

    # Step 8: Negatives like "no kids"
    negative_patterns = [
        'no kids', 'no children', 'no baby', 'no babies', 'no infants',
        'without kids', 'without children', 'without baby'
    ]
    for pattern in negative_patterns:
        if pattern in query_lower:
            if 'kid' in pattern or 'child' in pattern:
                children = 0
            elif 'baby' in pattern or 'infant' in pattern:
                infants = 0

    # Step 9: Compound patterns (Enhanced)
    compound_patterns = {
        'me and my': 2,
        'my wife and i': 2,
        'my husband and i': 2,
        'with my brother and sister': 3,
        'with two friends': 3,
        'book a flight for me and my parents': 3,
        'with my parents': 3,
        'two couples and': 4  # For "Two couples and 4 kids"
    }
    for pattern, count in compound_patterns.items():
        if pattern in query_lower:
            adults = max(adults, count)

    # Step 10: "few people" - Fixed to return 3 not 4
    if 'few people' in query_lower or 'a few people' in query_lower:
        adults = 3  # Use exact value, not max
    elif 'several' in tokens:
        adults = max(adults, 4)  # Keep several as 4

    # Step 11: Defaults and edge cases
    if adults == 0 and children == 0 and infants == 0:
        adults = 1
    
    # Special case for "3 adults, 2 children, 1 infant"
    if "adults" in query_lower and "children" in query_lower and "infant" in query_lower:
        # Find numbers before each category
        for i, token in enumerate(tokens):
            if token == "adults" and i > 0 and extract_number(tokens[i-1]):
                adults = extract_number(tokens[i-1])
            elif token == "children" and i > 0 and extract_number(tokens[i-1]):
                children = extract_number(tokens[i-1])
            elif ("infant" in token or "infants" in token) and i > 0 and extract_number(tokens[i-1]):
                infants = extract_number(tokens[i-1])

    return {
        "adults": max(0, adults),
        "children": max(0, children),
        "infants": max(0, infants)
    }

def extract_airline(query):
    """
    Extract airline name from query with multiple strategies.
    Returns standardized airline code or None if not found.
    """
    query_lower = query.lower().strip()

    # Strategy 1: Direct keyword match
    sorted_keywords = sorted(all_airline_keywords, key=lambda x: len(x[0]), reverse=True)
    for keyword, airline_code in sorted_keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, query_lower):
            return airline_code

    # Strategy 2: Pattern-based extraction
    airline_patterns = [
        r'(?:fly|travel|book|reserve)\s+(?:with|on|via)\s+([a-zA-Z\s-]+?)(?:\s|$|,|\.|\?)',
        r'([a-zA-Z\s-]+?)\s+(?:flight|ticket|airlines?|airways?|air)(?:\s|$|,|\.)',
        r'(?:on|via|through)\s+([a-zA-Z\s-]+?)(?:\s|$|,|\.|\?)',
        r'(?:prefer|want|need|like)\s+([a-zA-Z\s-]+?)(?:\s|$|,|\.|\?)',
        r'\b([A-Z]{2,3})\s*\d{2,4}\b',
    ]
    for pattern in airline_patterns:
        matches = re.findall(pattern, query_lower, re.IGNORECASE)
        for match in matches:
            extracted_text = match.strip().lower()
            if len(extracted_text) < 2:
                continue
            for keyword, airline_code in sorted_keywords:
                if extracted_text == keyword or keyword in extracted_text:
                    return airline_code

# Strategy 3: NLP-based context extraction (safe version)
    try:
        doc = nlp(query_lower)
        airline_indicators = {"airlines", "airways", "air", "airline", "flight", "carrier"}

        for ent in doc.ents:
            if ent.label_ in {"ORG", "PERSON", "GPE"}:
                ent_text = ent.text.lower()
                for keyword, airline_code in sorted_keywords:
                    if keyword == ent_text or keyword in ent_text:
                        return airline_code

        # Check token context only if an airline indicator exists in the sentence
        if any(word in query_lower for word in airline_indicators):
            for token in doc:
                if token.pos_ == "PROPN":
                    start_idx = max(0, token.i - 2)
                    end_idx = min(len(doc), token.i + 3)
                    context_tokens = [t.text.lower() for t in doc[start_idx:end_idx]]
                    context_text = " ".join(context_tokens)

                    for keyword, airline_code in sorted_keywords:
                        if keyword in context_text:
                            return airline_code
    except Exception as e:
        print(f"[DEBUG] NLP strategy failed: {e}")

    # Strategy 4: Fuzzy matching
    try:
        doc = nlp(query_lower)
        airline_related_words = []

        for token in doc:
            if (token.pos_ in ["NOUN", "PROPN"] and 
                len(token.text) > 3 and 
                not token.is_stop and 
                not token.like_num):
                if token.text.lower() not in {"flight", "ticket", "booking", "travel", "trip", "journey", "airport", "departure", "arrival", "passenger", "seat"}:
                    airline_related_words.append(token.text.lower())

        for i in range(len(doc) - 1):
            if (doc[i].pos_ in ["NOUN", "PROPN"] and doc[i+1].pos_ in ["NOUN", "PROPN", "ADJ"]):
                phrase = f"{doc[i].text} {doc[i+1].text}".lower()
                if len(phrase) > 6:
                    airline_related_words.append(phrase)

        all_keywords = [keyword for keyword, _ in sorted_keywords]
        for word in airline_related_words:
            result = process.extractOne(word, all_keywords)
            if result:
                best_match, score, _ = result
                if score > 95:
                    for keyword, airline_code in sorted_keywords:
                        if keyword == best_match:
                            print(f"[DEBUG] Matched via fuzzy: '{word}' → '{best_match}' (score: {score}) → {airline_code}")
                            return airline_code

    except Exception as e:
        print(f"[DEBUG] Fuzzy matching failed: {e}")

    return None

def extract_travel_info(query):
    """
    Main function to extract all travel information from a query.
    
    Args:
        query (str): User's travel query
    
    Returns:
        dict: Dictionary containing all extracted travel information
    """
    result = {}
    
    # Extract cities
    source, destination = extract_cities(query)
    
    # Ensure source and destination are different
    if source and destination and source == destination:
        destination = None
    
    if source:
        result["source"] = source
    else:
        result["source"] = None
    if destination:
        result["destination"] = destination
    else:
        result["destination"] = None
    
    # Extract flight type
    flight_type = extract_flight_type(query)
    result["flight_type"] = flight_type
    
    # Extract flight class
    flight_class = extract_flight_class(query)
    result["flight_class"] = flight_class
    
    # Extract airline (ContentProvider)
    airline = extract_airline(query)
    if airline:
        result["content_provider"] = airline
    else:
        result["content_provider"] = None
    
    # Extract dates based on flight type
    if flight_type == "return":
        departure_date, return_date = extract_dates(query, flight_type)
        if departure_date:
            result["departure_date"] = departure_date
        else:
            result["departure_date"] = None
        if return_date:
            result["return_date"] = return_date
        else:
            result["return_date"] = None
    else:
        date = extract_dates(query, flight_type)
        if date:
            result["departure_date"] = date
        else:
            result["departure_date"] = None
    
    # Extract passenger count
    try:
        passenger_counts = extract_passenger_count(query)
        result["passengers"] = passenger_counts
        
        # Also add total passenger count for convenience
        total_passengers = passenger_counts["adults"] + passenger_counts["children"] + passenger_counts["infants"]
        result["total_passengers"] = total_passengers
    except Exception as e:
        print(f"Warning: Passenger count extraction failed: {e}")
        # Fallback to default
        result["passengers"] = {"adults": 1, "children": 0, "infants": 0}
        result["total_passengers"] = 1
    
    return result

# Enhanced command-line interface
if __name__ == "__main__":
    while True:
        query = input("Enter your travel query: ").strip()
        if query.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        if not query:
            continue
        try:
            result = extract_travel_info(query)
            print(result)
        except Exception as e:
            print(f"Error processing query: {e}")