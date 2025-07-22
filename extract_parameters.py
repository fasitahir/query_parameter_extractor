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
        r'between\s+.*?\s+and\s+.*?(?:\d|today|tomorrow)',
        
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
            if score > 80:  # High threshold for class matching
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
        "today": today.strftime("%Y-%m-%d"),
        "tomorrow": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
        "day after tomorrow": (today + timedelta(days=2)).strftime("%Y-%m-%d")
    }
    
    # Fix common date format issues
    text_fixed = re.sub(r'(\d+)(st|nd|rd|th)\s+of\s+', r'\1\2 ', original_text)
    
    dates = []
    
    # Auto-detect flight type if not provided
    if flight_type is None:
        flight_type = extract_flight_type(text)
    
    if flight_type == "return":
        # Strategy 1: Look for "between X and Y" pattern
        between_pattern = r'between\s+(.*?)\s+and\s+(.*?)(?:\s|$|,|\.)'
        between_matches = re.findall(between_pattern, text_fixed, re.IGNORECASE)
        
        if between_matches:
            for match in between_matches:
                date1_text, date2_text = match
                date1_text = date1_text.strip().lower()
                date2_text = date2_text.strip().lower()
                
                # Clean up the date text (remove extra words)
                date1_text = re.sub(r'\b(of|the)\b', '', date1_text).strip()
                date2_text = re.sub(r'\b(of|the)\b', '', date2_text).strip()
                
                # Parse first date
                if date1_text in special_date_map:
                    dates.append(special_date_map[date1_text])
                else:
                    try:
                        cal = parsedatetime.Calendar()
                        time_struct, parse_status = cal.parse(date1_text)
                        if parse_status >= 1:
                            departure_date = datetime(*time_struct[:6])
                            dates.append(departure_date.strftime("%Y-%m-%d"))
                    except:
                        pass
                
                # Parse second date
                if date2_text in special_date_map:
                    dates.append(special_date_map[date2_text])
                else:
                    try:
                        cal = parsedatetime.Calendar()
                        time_struct, parse_status = cal.parse(date2_text)
                        if parse_status >= 1:
                            return_date = datetime(*time_struct[:6])
                            dates.append(return_date.strftime("%Y-%m-%d"))
                    except:
                        pass
                
                if len(dates) >= 2:
                    return dates[0], dates[1]
        
        # Strategy 2: Look for explicit date pairs with "and then" or "then"
        date_pair_patterns = [
            r'\b(today|tomorrow|day after tomorrow)\b.*?\b(?:and\s+(?:then\s+)?|then\s+)\b.*?\b(today|tomorrow|day after tomorrow)\b',
            r'\bon\s+([^,]+?)\s+and\s+(?:then\s+)?(?:on\s+)?([^,]+?)(?:\s|$|,)',
            r'\b(\d+(?:st|nd|rd|th)?(?:\s+\w+)?)\s+(?:and\s+(?:then\s+)?|then\s+|to\s+)(?:on\s+)?(\d+(?:st|nd|rd|th)?(?:\s+\w+)?)(?:\s|$|,)',
            r'(\d+(?:st|nd|rd|th)?\s+\w+)\s+(?:to|and|until)\s+(\d+(?:st|nd|rd|th)?\s+\w+)',
        ]
        
        for pattern in date_pair_patterns:
            matches = re.findall(pattern, text_fixed, re.IGNORECASE)
            if matches:
                for match in matches:
                    if len(match) == 2:
                        date1_text, date2_text = match
                        date1_text = date1_text.strip().lower()
                        date2_text = date2_text.strip().lower()
                        
                        # Parse first date
                        if date1_text in special_date_map:
                            dates.append(special_date_map[date1_text])
                        else:
                            try:
                                cal = parsedatetime.Calendar()
                                time_struct, parse_status = cal.parse(date1_text)
                                if parse_status >= 1:
                                    departure_date = datetime(*time_struct[:6])
                                    dates.append(departure_date.strftime("%Y-%m-%d"))
                            except:
                                pass
                        
                        # Parse second date
                        if date2_text in special_date_map:
                            dates.append(special_date_map[date2_text])
                        else:
                            try:
                                cal = parsedatetime.Calendar()
                                time_struct, parse_status = cal.parse(date2_text)
                                if parse_status >= 1:
                                    return_date = datetime(*time_struct[:6])
                                    dates.append(return_date.strftime("%Y-%m-%d"))
                            except:
                                pass
                        
                        if len(dates) >= 2:
                            return dates[0], dates[1]
        
        # Strategy 3: If no explicit pairs found, collect all dates
        if len(dates) < 2:
            dates = []
            
            # Collect special dates
            for special_word in ["today", "tomorrow", "day after tomorrow"]:
                if special_word in original_text:
                    if special_date_map[special_word] not in dates:
                        dates.append(special_date_map[special_word])
            
            # Try to parse additional dates from the text
            if len(dates) < 2:
                # Remove special words that we've already processed
                text_without_special = text_fixed
                for special_word in special_date_map.keys():
                    if special_word in text_without_special:
                        text_without_special = text_without_special.replace(special_word, "", 1)
                
                # Extract date-like patterns
                date_patterns = [
                    r'\d+(?:st|nd|rd|th)?\s+(?:of\s+)?\w+',  # "15th December" or "15th of December"
                    r'\w+\s+\d+(?:st|nd|rd|th)?',            # "December 15th"
                    r'\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?',   # "12/15" or "12/15/2024"
                ]
                
                for pattern in date_patterns:
                    matches = re.findall(pattern, text_without_special)
                    for match in matches:
                        if len(dates) >= 2:
                            break
                        try:
                            cal = parsedatetime.Calendar()
                            time_struct, parse_status = cal.parse(match.strip())
                            if parse_status >= 1:
                                parsed_date = datetime(*time_struct[:6])
                                date_str = parsed_date.strftime("%Y-%m-%d")
                                if date_str not in dates:
                                    dates.append(date_str)
                        except:
                            pass
        
        # Return results for return flight
        if len(dates) >= 2:
            return dates[0], dates[1]
        elif len(dates) == 1:
            return dates[0], None
        else:
            # Last resort: try parsing the entire text
            try:
                cal = parsedatetime.Calendar()
                time_struct, parse_status = cal.parse(text_fixed)
                if parse_status >= 1:
                    departure_date = datetime(*time_struct[:6])
                    return departure_date.strftime("%Y-%m-%d"), None
            except:
                pass
            return None, None
    
    else:
        # One-way flight - extract single date
        # Check special dates first
        for special_word, special_date in special_date_map.items():
            if special_word in original_text:
                return special_date
        
        # Try parsedatetime for other dates
        try:
            cal = parsedatetime.Calendar()
            time_struct, parse_status = cal.parse(text_fixed)
            if parse_status >= 1:
                parsed_date = datetime(*time_struct[:6])
                return parsed_date.strftime("%Y-%m-%d")
        except:
            pass
        
        return None

def extract_travel_info(query):
    """
    Main function to extract all travel information from a query.
    """
    result = {}
    
    # Extract cities
    source, destination = extract_cities(query)
    
    # Ensure source and destination are different
    if source and destination and source == destination:
        destination = None
    
    if source:
        result["source"] = source
    if destination:
        result["destination"] = destination
    
    # Extract flight type
    flight_type = extract_flight_type(query)
    result["flight_type"] = flight_type
    
    # Extract flight class
    flight_class = extract_flight_class(query)
    result["flight_class"] = flight_class
    
    # Extract dates based on flight type
    if flight_type == "return":
        departure_date, return_date = extract_dates(query, flight_type)
        if departure_date:
            result["departure_date"] = departure_date
        if return_date:
            result["return_date"] = return_date
        else:
            result["return_date"] = None
    else:
        date = extract_dates(query, flight_type)
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