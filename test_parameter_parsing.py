import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from datetime import datetime, timedelta

# Import the module to test (assuming it's saved as travel_extractor.py)
# You may need to adjust this import based on your file structure
try:
    from extract_parameters import (
        extract_cities, extract_flight_type, extract_flight_class, 
        extract_dates, extract_passenger_count_llm, extract_travel_info,
        correct_spelling, extract_cities_multiword
    )
except ImportError:
    # If the above doesn't work, try this alternative
    import importlib.util
    spec = importlib.util.spec_from_file_location("travel_extractor", "paste.py")
    travel_extractor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(travel_extractor)
    
    extract_cities = travel_extractor.extract_cities
    extract_flight_type = travel_extractor.extract_flight_type
    extract_flight_class = travel_extractor.extract_flight_class
    extract_dates = travel_extractor.extract_dates
    extract_passenger_count_llm = travel_extractor.extract_passenger_count_llm
    extract_travel_info = travel_extractor.extract_travel_info
    correct_spelling = travel_extractor.correct_spelling
    extract_cities_multiword = travel_extractor.extract_cities_multiword


class TestCityExtraction(unittest.TestCase):
    """Test city extraction functionality"""
    
    def test_basic_city_extraction(self):
        """Test basic city name extraction"""
        source, destination = extract_cities("flight from lahore to karachi")
        self.assertEqual(source, "LHE")
        self.assertEqual(destination, "KHI")
    
    def test_iata_code_extraction(self):
        """Test IATA code extraction"""
        source, destination = extract_cities("flight from LHE to KHI")
        self.assertEqual(source, "LHE")
        self.assertEqual(destination, "KHI")
    
    def test_mixed_city_iata(self):
        """Test mixed city names and IATA codes"""
        source, destination = extract_cities("from lahore to KHI")
        self.assertEqual(source, "LHE")
        self.assertEqual(destination, "KHI")
    
    def test_multi_word_cities(self):
        """Test multi-word city extraction"""
        source, destination = extract_cities("from dera ghazi khan to rahim yar khan")
        self.assertEqual(source, "DEA")
        self.assertEqual(destination, "RYK")
    
    def test_single_city_as_destination(self):
        """Test single city mentioned with 'to' indicator"""
        source, destination = extract_cities("want to go to karachi")
        self.assertIsNone(source)
        self.assertEqual(destination, "KHI")
    
    def test_single_city_as_source(self):
        """Test single city mentioned without clear direction"""
        source, destination = extract_cities("flight from lahore")
        self.assertEqual(source, "LHE")
        self.assertIsNone(destination)
    
    def test_no_cities_found(self):
        """Test when no cities are found"""
        source, destination = extract_cities("book a flight tomorrow")
        self.assertIsNone(source)
        self.assertIsNone(destination)
    
    def test_same_city_mentioned_twice(self):
        """Test handling of same city mentioned multiple times"""
        source, destination = extract_cities("from lahore to lahore")
        self.assertEqual(source, "LHE")
        self.assertIsNone(destination)


class TestFlightTypeExtraction(unittest.TestCase):
    """Test flight type extraction functionality"""
    
    def test_explicit_return_keywords(self):
        """Test explicit return flight keywords"""
        self.assertEqual(extract_flight_type("book a return flight"), "return")
        self.assertEqual(extract_flight_type("round trip ticket"), "return")
        self.assertEqual(extract_flight_type("round-trip flight"), "return")
        self.assertEqual(extract_flight_type("two way journey"), "return")
    
    def test_back_patterns(self):
        """Test 'back' patterns indicating return"""
        self.assertEqual(extract_flight_type("go to karachi and back to lahore"), "return")
        self.assertEqual(extract_flight_type("fly to islamabad then back"), "return")
        self.assertEqual(extract_flight_type("travel there and back"), "return")
    
    def test_date_range_patterns(self):
        """Test date range patterns suggesting return"""
        self.assertEqual(extract_flight_type("between 10th and 15th"), "return")
        self.assertEqual(extract_flight_type("from 10th to 15th january"), "return")
    
    def test_one_way_default(self):
        """Test default one-way classification"""
        self.assertEqual(extract_flight_type("flight to karachi"), "one_way")
        self.assertEqual(extract_flight_type("book ticket tomorrow"), "one_way")
        self.assertEqual(extract_flight_type("going to islamabad"), "one_way")
    
    def test_conservative_return_detection(self):
        """Test that system is conservative about return detection"""
        # These should NOT be classified as return
        self.assertEqual(extract_flight_type("flight to karachi and hotel"), "one_way")
        self.assertEqual(extract_flight_type("going to see family"), "one_way")


class TestFlightClassExtraction(unittest.TestCase):
    """Test flight class extraction functionality"""
    
    def test_explicit_class_mentions(self):
        """Test explicit class mentions"""
        self.assertEqual(extract_flight_class("business class flight"), "business")
        self.assertEqual(extract_flight_class("first class ticket"), "first")
        self.assertEqual(extract_flight_class("economy class seat"), "economy")
        self.assertEqual(extract_flight_class("premium economy"), "premium_economy")
    
    def test_class_variations(self):
        """Test various class name variations"""
        self.assertEqual(extract_flight_class("biz class"), "business")
        self.assertEqual(extract_flight_class("first-class"), "first")
        self.assertEqual(extract_flight_class("coach seat"), "economy")
        self.assertEqual(extract_flight_class("executive class"), "business")
    
    def test_abbreviated_classes(self):
        """Test abbreviated class codes"""
        self.assertEqual(extract_flight_class("J class ticket"), "business")
        self.assertEqual(extract_flight_class("F class seat"), "first")
        self.assertEqual(extract_flight_class("Y class flight"), "economy")
    
    def test_default_economy(self):
        """Test default to economy when no class specified"""
        self.assertEqual(extract_flight_class("flight to karachi"), "economy")
        self.assertEqual(extract_flight_class("book ticket tomorrow"), "economy")
    
    def test_context_based_inference(self):
        """Test context-based class inference"""
        self.assertEqual(extract_flight_class("expensive luxury flight"), "first")
        self.assertEqual(extract_flight_class("corporate travel meeting"), "business")


class TestDateExtraction(unittest.TestCase):
    """Test date extraction functionality"""
    
    def setUp(self):
        self.today = datetime.now()
        self.tomorrow = (self.today + timedelta(days=1)).strftime("%Y-%m-%d")
        self.day_after_tomorrow = (self.today + timedelta(days=2)).strftime("%Y-%m-%d")
    
    def test_special_date_words(self):
        """Test special date word extraction"""
        self.assertEqual(extract_dates("flight tomorrow", "one_way"), self.tomorrow)
        self.assertEqual(extract_dates("travel today", "one_way"), self.today.strftime("%Y-%m-%d"))
    
    def test_return_flight_dates(self):
        """Test return flight date extraction"""
        departure, return_date = extract_dates("between tomorrow and day after tomorrow", "return")
        self.assertEqual(departure, self.tomorrow)
        self.assertEqual(return_date, self.day_after_tomorrow)
    
    def test_explicit_date_formats(self):
        """Test various explicit date formats"""
        # Note: These tests might need adjustment based on current date
        result = extract_dates("15th january", "one_way")
        self.assertIsNotNone(result)
        
        result = extract_dates("jan 15", "one_way")
        self.assertIsNotNone(result)
    
    def test_no_date_found(self):
        """Test when no date is found"""
        self.assertIsNone(extract_dates("flight to karachi", "one_way"))
    
    def test_return_date_patterns(self):
        """Test various return date patterns"""
        departure, return_date = extract_dates("go tomorrow and back day after tomorrow", "return")
        self.assertEqual(departure, self.tomorrow)
        self.assertEqual(return_date, self.day_after_tomorrow)


class TestPassengerCountExtraction(unittest.TestCase):
    """Test passenger count extraction functionality"""
    
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'})
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_single_passenger(self, mock_model_class, mock_configure):
        """Test single passenger extraction"""
        # Mock the Gemini response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"adults": 1, "children": 0, "infants": 0}'
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        result = extract_passenger_count_llm("I want to travel")
        self.assertEqual(result["adults"], 1)
        self.assertEqual(result["children"], 0)
        self.assertEqual(result["infants"], 0)
    
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'})
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_family_travel(self, mock_model_class, mock_configure):
        """Test family travel extraction"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"adults": 2, "children": 1, "infants": 0}'
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        result = extract_passenger_count_llm("me and my wife with our child")
        self.assertEqual(result["adults"], 2)
        self.assertEqual(result["children"], 1)
        self.assertEqual(result["infants"], 0)
    
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'})
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_llm_failure_fallback(self, mock_model_class, mock_configure):
        """Test fallback when LLM fails"""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model
        
        result = extract_passenger_count_llm("travel for 5 people")
        # Should fallback to default
        self.assertEqual(result["adults"], 1)
        self.assertEqual(result["children"], 0)
        self.assertEqual(result["infants"], 0)


class TestIntegratedTravelExtraction(unittest.TestCase):
    """Test the main integrated travel extraction function"""
    
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'})
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_complete_query_extraction(self, mock_model_class, mock_configure):
        """Test complete query extraction"""
        # Mock the Gemini response for passenger count
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"adults": 1, "children": 0, "infants": 0}'
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        query = "business class return flight from lahore to karachi tomorrow"
        result = extract_travel_info(query)
        
        # Check all extracted information
        self.assertEqual(result["source"], "LHE")
        self.assertEqual(result["destination"], "KHI")
        self.assertEqual(result["flight_type"], "return")
        self.assertEqual(result["flight_class"], "business")
        self.assertIn("departure_date", result)
        self.assertEqual(result["passengers"]["adults"], 1)
        self.assertEqual(result["total_passengers"], 1)
    
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'})
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_minimal_query(self, mock_model_class, mock_configure):
        """Test minimal query extraction"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"adults": 1, "children": 0, "infants": 0}'
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        query = "flight to karachi"
        result = extract_travel_info(query)
        
        self.assertIsNone(result.get("source"))
        self.assertEqual(result["destination"], "KHI")
        self.assertEqual(result["flight_type"], "one_way")
        self.assertEqual(result["flight_class"], "economy")


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_spelling_correction(self):
        """Test spelling correction function"""
        # Note: This test depends on the autocorrect library behavior
        corrected = correct_spelling("flihgt")
        self.assertIsInstance(corrected, str)
    
    def test_multiword_city_extraction(self):
        """Test multi-word city extraction specifically"""
        cities = extract_cities_multiword("from dera ghazi khan to karachi")
        self.assertTrue(len(cities) >= 1)
        # Should find IATA codes for cities
        city_codes = [city[0] for city in cities]
        self.assertIn("DEA", city_codes)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def test_empty_query(self):
        """Test empty query handling"""
        result = extract_cities("")
        self.assertIsNone(result[0])
        self.assertIsNone(result[1])
        
        flight_type = extract_flight_type("")
        self.assertEqual(flight_type, "one_way")
    
    def test_very_long_query(self):
        """Test very long query handling"""
        long_query = "I want to book a flight " * 100 + "from lahore to karachi"
        source, destination = extract_cities(long_query)
        self.assertEqual(source, "LHE")
        self.assertEqual(destination, "KHI")
    
    def test_special_characters(self):
        """Test handling of special characters"""
        source, destination = extract_cities("flight from lahore!!! to karachi???")
        self.assertEqual(source, "LHE")
        self.assertEqual(destination, "KHI")
    
    def test_mixed_case_input(self):
        """Test mixed case input handling"""
        source, destination = extract_cities("FLIGHT FROM LaHoRe TO kArAcHi")
        self.assertEqual(source, "LHE")
        self.assertEqual(destination, "KHI")


class TestRealWorldQueries(unittest.TestCase):
    """Test real-world query examples"""
    
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'})
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_realistic_queries(self, mock_model_class, mock_configure):
        """Test realistic user queries"""
        # Mock the Gemini response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"adults": 2, "children": 1, "infants": 0}'
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        queries = [
            "I need to book a business class flight from Lahore to Islamabad for tomorrow",
            "Return ticket from KHI to LHE for me and my family",
            "Cheap flight to Karachi next week",
            "Business class round trip from Lahore to Dubai", # Dubai not in our list
        ]
        
        for query in queries:
            result = extract_travel_info(query)
            # Should at least extract some information without errors
            self.assertIsInstance(result, dict)
            self.assertIn("flight_type", result)
            self.assertIn("flight_class", result)


if __name__ == "__main__":
    # Set up test environment
    print("Running Travel Information Extraction Tests")
    print("=" * 50)
    
    # Check if required dependencies are available
    try:
        import spacy
        import rapidfuzz
        import parsedatetime
        import autocorrect
        print("✓ All dependencies available")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install spacy rapidfuzz parsedatetime autocorrect python-dotenv google-generativeai")
        sys.exit(1)
    
    # Check if spaCy model is available
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("✓ spaCy English model available")
    except OSError:
        print("✗ spaCy English model not found")
        print("Please install: python -m spacy download en_core_web_sm")
        sys.exit(1)
    
    # Run tests with different verbosity levels
    if len(sys.argv) > 1 and sys.argv[1] == "-v":
        verbosity = 2
    else:
        verbosity = 1
    
    # Create test suite
    test_classes = [
        TestCityExtraction,
        TestFlightTypeExtraction, 
        TestFlightClassExtraction,
        TestDateExtraction,
        TestPassengerCountExtraction,
        TestIntegratedTravelExtraction,
        TestUtilityFunctions,
        TestEdgeCases,
        TestRealWorldQueries
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split(chr(10))[-2]}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split(chr(10))[-2]}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)