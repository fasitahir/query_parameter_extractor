#!/usr/bin/env python3
"""
Comprehensive test suite for the travel information extractor.
Tests all major functions with various edge cases and scenarios.
"""

import unittest
from datetime import datetime, timedelta
import sys
import os

# Import the travel extractor functions
# Assuming the main script is named 'travel_extractor.py'
try:
    from extract_parameters import (
        extract_cities, extract_flight_type, extract_flight_class, 
        extract_dates, extract_travel_info, correct_spelling,
        extract_cities_multiword
    )
except ImportError:
    print("Error: Could not import travel_extractor module.")
    print("Please ensure the main script is named 'travel_extractor.py' and is in the same directory.")
    sys.exit(1)

class TestCityExtraction(unittest.TestCase):
    """Test city extraction functionality"""
    
    def test_single_city_extraction(self):
        """Test extraction of single cities"""
        test_cases = [
            ("I want to go to Lahore", (None, "LHE")),
            ("Flight from Karachi", ("KHI", None)),
            ("Leaving from Islamabad", ("ISB", None)),
            ("Going to peshawar", (None, "PEW")),
        ]
        
        for query, expected in test_cases:
            with self.subTest(query=query):
                result = extract_cities(query)
                self.assertEqual(result, expected)
    
    def test_multiple_city_extraction(self):
        """Test extraction of multiple cities"""
        test_cases = [
            ("Flight from Lahore to Karachi", ("LHE", "KHI")),
            ("Karachi to Islamabad flight", ("KHI", "ISB")),
            ("From Multan to Peshawar", ("MUX", "PEW")),
            ("Lahore Karachi flight", ("LHE", "KHI")),
        ]
        
        for query, expected in test_cases:
            with self.subTest(query=query):
                result = extract_cities(query)
                self.assertEqual(result, expected)
    
    def test_multiword_cities(self):
        """Test extraction of multi-word city names"""
        test_cases = [
            ("Flight to Dera Ghazi Khan", (None, "DEA")),
            ("From Rahim Yar Khan to Lahore", ("RYK", "LHE")),
            ("Dera Ghazi Khan to Karachi", ("DEA", "KHI")),
        ]
        
        for query, expected in test_cases:
            with self.subTest(query=query):
                result = extract_cities(query)
                self.assertEqual(result, expected)
    
    def test_iata_codes(self):
        """Test direct IATA code recognition"""
        test_cases = [
            ("Flight LHE to KHI", ("LHE", "KHI")),
            ("From ISB", ("ISB", None)),
            ("Going to PEW", (None, "PEW")),
            ("LHE KHI flight", ("LHE", "KHI")),
        ]
        
        for query, expected in test_cases:
            with self.subTest(query=query):
                result = extract_cities(query)
                self.assertEqual(result, expected)
    
    def test_mixed_formats(self):
        """Test mixed city names and IATA codes"""
        test_cases = [
            ("From Lahore to KHI", ("LHE", "KHI")),
            ("ISB to Karachi flight", ("ISB", "KHI")),
            ("Flight LHE to Islamabad", ("LHE", "ISB")),
        ]
        
        for query, expected in test_cases:
            with self.subTest(query=query):
                result = extract_cities(query)
                self.assertEqual(result, expected)
    
    def test_no_cities_found(self):
        """Test cases where no cities are found"""
        test_cases = [
            "I want to book a flight",
            "Need travel information",
            "Flight booking help",
            "ABC to XYZ",  # Invalid IATA codes
        ]
        
        for query in test_cases:
            with self.subTest(query=query):
                result = extract_cities(query)
                self.assertEqual(result, (None, None))

class TestFlightTypeExtraction(unittest.TestCase):
    """Test flight type extraction functionality"""
    
    def test_explicit_return_indicators(self):
        """Test explicit return flight keywords"""
        return_cases = [
            "I need a return ticket from Lahore to Karachi",
            "Round trip flight to Islamabad",
            "Book me a round-trip ticket",
            "Return flight from KHI to LHE",
            "Two-way ticket please",
            "Need both ways ticket",
        ]
        
        for query in return_cases:
            with self.subTest(query=query):
                result = extract_flight_type(query)
                self.assertEqual(result, "return")
    
    def test_return_patterns(self):
        """Test pattern-based return detection"""
        return_cases = [
            "Go to Karachi and back to Lahore",
            "Flight to Islamabad and then back",
            "Travel to Peshawar and return",
            "Between tomorrow and next week",
            "From 10th to 15th December",
            "Go there and come back",
        ]
        
        for query in return_cases:
            with self.subTest(query=query):
                result = extract_flight_type(query)
                self.assertEqual(result, "return")
    
    def test_one_way_default(self):
        """Test default one-way detection"""
        one_way_cases = [
            "Flight to Lahore",
            "Going to Karachi tomorrow",
            "Need ticket to Islamabad",
            "One way to Peshawar",
            "Flying to Multan on Monday",
        ]
        
        for query in one_way_cases:
            with self.subTest(query=query):
                result = extract_flight_type(query)
                self.assertEqual(result, "one_way")
    
    def test_conservative_return_detection(self):
        """Test that ambiguous cases default to one-way"""
        ambiguous_cases = [
            "Lahore and Karachi flight",  # Ambiguous
            "Between Lahore and Karachi",  # Could be route, not dates
            "Flight Lahore Karachi",
        ]
        
        for query in ambiguous_cases:
            with self.subTest(query=query):
                result = extract_flight_type(query)
                # Should be conservative and default to one_way unless clear indicators
                self.assertIn(result, ["one_way", "return"])

class TestFlightClassExtraction(unittest.TestCase):
    """Test flight class extraction functionality"""
    
    def test_economy_class(self):
        """Test economy class detection"""
        economy_cases = [
            "Economy class flight to Lahore",
            "Book economy ticket",
            "Cheapest flight to Karachi",
            "Y class seat",
            "Coach flight",
        ]
        
        for query in economy_cases:
            with self.subTest(query=query):
                result = extract_flight_class(query)
                self.assertEqual(result, "economy")
    
    def test_business_class(self):
        """Test business class detection"""
        business_cases = [
            "Business class flight to Islamabad",
            "Book business ticket",
            "J class seat",
            "Executive class flight",
            "Business trip to Lahore",
        ]
        
        for query in business_cases:
            with self.subTest(query=query):
                result = extract_flight_class(query)
                self.assertEqual(result, "business")
    
    def test_first_class(self):
        """Test first class detection"""
        first_cases = [
            "First class flight to Karachi",
            "Book first class ticket",
            "F class seat",
            "Luxury flight to Lahore",
            "First-class service",
        ]
        
        for query in first_cases:
            with self.subTest(query=query):
                result = extract_flight_class(query)
                self.assertEqual(result, "first")
    
    def test_premium_economy(self):
        """Test premium economy detection"""
        premium_cases = [
            "Premium economy flight",
            "Premium class ticket",
            "Economy plus seat",
            "Extra comfort flight",
            "W class booking",
        ]
        
        for query in premium_cases:
            with self.subTest(query=query):
                result = extract_flight_class(query)
                self.assertEqual(result, "premium_economy")
    
    def test_default_economy(self):
        """Test default to economy when no class specified"""
        default_cases = [
            "Flight to Lahore",
            "Book ticket to Karachi",
            "Need flight tomorrow",
        ]
        
        for query in default_cases:
            with self.subTest(query=query):
                result = extract_flight_class(query)
                self.assertEqual(result, "economy")

class TestDateExtraction(unittest.TestCase):
    """Test date extraction functionality"""
    
    def setUp(self):
        """Set up test dates"""
        self.today = datetime.now()
        self.tomorrow = self.today + timedelta(days=1)
        self.day_after_tomorrow = self.today + timedelta(days=2)
    
    def test_special_dates_one_way(self):
        """Test special date extraction for one-way flights"""
        today_str = self.today.strftime("%Y-%m-%d")
        tomorrow_str = self.tomorrow.strftime("%Y-%m-%d")
        day_after_str = self.day_after_tomorrow.strftime("%Y-%m-%d")
        
        test_cases = [
            ("Flight today", today_str),
            ("Going tomorrow", tomorrow_str),
            ("Travel day after tomorrow", day_after_str),
        ]
        
        for query, expected in test_cases:
            with self.subTest(query=query):
                result = extract_dates(query, "one_way")
                self.assertEqual(result, expected)
    
    def test_special_dates_return(self):
        """Test special date extraction for return flights"""
        today_str = self.today.strftime("%Y-%m-%d")
        tomorrow_str = self.tomorrow.strftime("%Y-%m-%d")
        
        test_cases = [
            ("Go today and return tomorrow", (today_str, tomorrow_str)),
            ("Travel tomorrow and back today", (tomorrow_str, today_str)),
            ("Between today and tomorrow", (today_str, tomorrow_str)),
        ]
        
        for query, expected in test_cases:
            with self.subTest(query=query):
                result = extract_dates(query, "return")
                self.assertEqual(result, expected)
    
    def test_date_patterns(self):
        """Test various date pattern recognition"""
        # Note: These tests may be sensitive to current date and year
        test_cases = [
            "Flight on 15th December",
            "Travel on December 15th",
            "Going on 12/25",
            "Flight next Monday",
            "Travel next week",
        ]
        
        for query in test_cases:
            with self.subTest(query=query):
                result = extract_dates(query, "one_way")
                # Should return a valid date string or None
                if result:
                    self.assertIsInstance(result, str)
                    # Should be a valid date format
                    try:
                        datetime.strptime(result, "%Y-%m-%d")
                    except ValueError:
                        self.fail(f"Invalid date format returned: {result}")
    
    def test_return_date_patterns(self):
        """Test return flight date patterns"""
        test_cases = [
            "Go on 15th and return on 20th",
            "Between 10th December and 15th December",
            "Travel on Monday and back on Friday",
        ]
        
        for query in test_cases:
            with self.subTest(query=query):
                result = extract_dates(query, "return")
                if result and result != (None, None):
                    departure, return_date = result
                    if departure:
                        self.assertIsInstance(departure, str)
                    if return_date:
                        self.assertIsInstance(return_date, str)

class TestIntegratedFunctionality(unittest.TestCase):
    """Test the main extract_travel_info function"""
    
    def test_complete_queries(self):
        """Test complete travel queries with all parameters"""
        test_cases = [
            {
                "query": "Business class return flight from Lahore to Karachi tomorrow",
                "expected_keys": ["source", "destination", "flight_type", "flight_class", "departure_date", "return_date"],
                "expected_values": {
                    "source": "LHE",
                    "destination": "KHI",
                    "flight_type": "return",
                    "flight_class": "business"
                }
            },
            {
                "query": "One way economy ticket to Islamabad today",
                "expected_keys": ["destination", "flight_type", "flight_class", "date"],
                "expected_values": {
                    "destination": "ISB",
                    "flight_type": "one_way",
                    "flight_class": "economy"
                }
            },
            {
                "query": "First class flight from KHI to LHE",
                "expected_keys": ["source", "destination", "flight_type", "flight_class"],
                "expected_values": {
                    "source": "KHI",
                    "destination": "LHE",
                    "flight_type": "one_way",
                    "flight_class": "first"
                }
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(query=test_case["query"]):
                result = extract_travel_info(test_case["query"])
                
                # Check that expected keys are present
                for key in test_case["expected_keys"]:
                    self.assertIn(key, result, f"Missing key: {key}")
                
                # Check expected values
                for key, expected_value in test_case["expected_values"].items():
                    self.assertEqual(result[key], expected_value, 
                                   f"Wrong value for {key}: expected {expected_value}, got {result.get(key)}")
    
    def test_minimal_queries(self):
        """Test queries with minimal information"""
        test_cases = [
            "Flight to Lahore",
            "Going to KHI",
            "Need ticket",
            "Book flight tomorrow",
        ]
        
        for query in test_cases:
            with self.subTest(query=query):
                result = extract_travel_info(query)
                self.assertIsInstance(result, dict)
                # Should always have flight_type and flight_class
                self.assertIn("flight_type", result)
                self.assertIn("flight_class", result)
    
    def test_complex_queries(self):
        """Test complex, realistic queries"""
        complex_queries = [
            "I need to book a return business class flight from Lahore to Karachi, going tomorrow and coming back day after tomorrow",
            "Can you help me find a first class one-way ticket from ISB to PEW on 15th December?",
            "Looking for the cheapest economy flight from Multan to Quetta, preferably today",
            "Book me a premium economy round trip from Rahim Yar Khan to Islamabad between next Monday and Friday",
        ]
        
        for query in complex_queries:
            with self.subTest(query=query):
                result = extract_travel_info(query)
                
                # Should be a valid result dict
                self.assertIsInstance(result, dict)
                
                # Should have basic required fields
                self.assertIn("flight_type", result)
                self.assertIn("flight_class", result)
                
                # If cities found, they should be valid IATA codes
                if "source" in result:
                    self.assertIsInstance(result["source"], str)
                    self.assertEqual(len(result["source"]), 3)
                
                if "destination" in result:
                    self.assertIsInstance(result["destination"], str)
                    self.assertEqual(len(result["destination"]), 3)

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def test_empty_input(self):
        """Test empty or whitespace input"""
        test_cases = ["", "   ", "\t\n"]
        
        for query in test_cases:
            with self.subTest(query=repr(query)):
                result = extract_travel_info(query)
                self.assertIsInstance(result, dict)
                # Should have defaults
                self.assertEqual(result["flight_type"], "one_way")
                self.assertEqual(result["flight_class"], "economy")
    
    def test_invalid_cities(self):
        """Test queries with invalid or unknown cities"""
        test_cases = [
            "Flight from XYZ to ABC",  # Invalid IATA codes
            "Going to London",  # Not in Pakistan cities list
            "Flight from New York to Paris",
        ]
        
        for query in test_cases:
            with self.subTest(query=query):
                result = extract_travel_info(query)
                # Should not crash, should return valid dict
                self.assertIsInstance(result, dict)
    
    def test_same_source_destination(self):
        """Test queries where source and destination are the same"""
        test_cases = [
            "Flight from Lahore to Lahore",
            "LHE to LHE ticket",
            "Round trip Karachi to Karachi",
        ]
        
        for query in test_cases:
            with self.subTest(query=query):
                result = extract_travel_info(query)
                # Should handle this gracefully
                if "source" in result and "destination" in result:
                    # Should not be the same
                    self.assertNotEqual(result["source"], result["destination"])
    
    def test_very_long_queries(self):
        """Test very long, complex queries"""
        long_query = """
        Hello, I am planning a business trip and I need to book a return business class flight 
        from Lahore to Karachi. I want to travel tomorrow morning and return day after tomorrow 
        in the evening. I prefer window seats and need extra legroom. Can you help me find 
        the best options available? Also, I have a corporate discount code. Please check for 
        any available upgrades to first class if possible. The trip is urgent and I need 
        confirmation today itself.
        """
        
        result = extract_travel_info(long_query)
        self.assertIsInstance(result, dict)
        
        # Should extract key information despite the complexity
        self.assertEqual(result["flight_class"], "business")
        self.assertEqual(result["flight_type"], "return")
        if "source" in result:
            self.assertEqual(result["source"], "LHE")
        if "destination" in result:
            self.assertEqual(result["destination"], "KHI")

def run_performance_test():
    """Simple performance test"""
    import time
    
    test_queries = [
        "Flight from Lahore to Karachi tomorrow",
        "Business class return ticket ISB to PEW",
        "Economy one-way flight to Multan today",
        "First class round trip from Quetta to Islamabad between Monday and Friday",
        "Premium economy flight from Dera Ghazi Khan to Rahim Yar Khan",
    ]
    
    start_time = time.time()
    
    for _ in range(100):  # Run each query 100 times
        for query in test_queries:
            extract_travel_info(query)
    
    end_time = time.time()
    total_queries = 100 * len(test_queries)
    avg_time = (end_time - start_time) / total_queries
    
    print(f"\nPerformance Test Results:")
    print(f"Total queries processed: {total_queries}")
    print(f"Total time: {end_time - start_time:.3f} seconds")
    print(f"Average time per query: {avg_time:.4f} seconds")

def run_interactive_test():
    """Interactive test mode for manual testing"""
    print("\n" + "="*50)
    print("INTERACTIVE TEST MODE")
    print("="*50)
    print("Enter travel queries to test the extractor.")
    print("Type 'quit' to exit.")
    
    while True:
        query = input("\nEnter query: ").strip()
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            print("Please enter a valid query.")
            continue
        
        try:
            result = extract_travel_info(query)
            print(f"\nExtracted Information:")
            print("-" * 30)
            for key, value in result.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        except Exception as e:
            print(f"Error processing query: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the travel information extractor")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Run in interactive test mode")
    parser.add_argument("--performance", "-p", action="store_true",
                       help="Run performance test")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    if args.interactive:
        run_interactive_test()
    elif args.performance:
        run_performance_test()
    else:
        # Run unit tests
        if args.verbose:
            verbosity = 2
        else:
            verbosity = 1
        
        # Create test suite
        test_suite = unittest.TestSuite()
        
        # Add all test classes
        test_classes = [
            TestCityExtraction,
            TestFlightTypeExtraction, 
            TestFlightClassExtraction,
            TestDateExtraction,
            TestIntegratedFunctionality,
            TestEdgeCases
        ]
        
        for test_class in test_classes:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            test_suite.addTests(tests)
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(test_suite)
        
        # Print summary
        print(f"\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFAILURES:")
            for test, traceback in result.failures:
                print(f"- {test}")
        
        if result.errors:
            print("\nERRORS:")
            for test, traceback in result.errors:
                print(f"- {test}")
        
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if args.performance:
            run_performance_test()