import unittest
from extract_parameters import extract_travel_info  # adjust import based on actual file name
from datetime import datetime, timedelta


class TestTravelExtraction(unittest.TestCase):

    def setUp(self):
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.day_after_tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

    # ✅ Happy Path Cases
    def test_simple_from_to(self):
        result = extract_travel_info("I want to book a flight from Lahore to Karachi tomorrow")
        self.assertEqual(result, {'source': 'LHE', 'destination': 'KHI', 'date': self.tomorrow})

    def test_variation_phrasing(self):
        result = extract_travel_info("Flying from Islamabad heading to Multan day after tomorrow")
        self.assertEqual(result, {'source': 'ISB', 'destination': 'MUX', 'date': self.day_after_tomorrow})

    def test_implicit_direction(self):
        result = extract_travel_info("I am in Karachi and going to Peshawar")
        self.assertEqual(result, {'source': 'KHI', 'destination': 'PEW'})

    def test_only_date(self):
        result = extract_travel_info("I want to travel today")
        self.assertEqual(result, {'date': self.today})

    def test_proper_date_parsing(self):
        result = extract_travel_info("Book a flight from Lahore to Quetta on 25th December")
        self.assertEqual(result['source'], 'LHE')
        self.assertEqual(result['destination'], 'UET')
        self.assertTrue(result['date'].endswith("12-25"))

    # ❌ Edge Cases / Failure Scenarios
    def test_same_source_and_destination(self):
        result = extract_travel_info("Book a flight from Lahore to Lahore tomorrow")
        self.assertEqual(result, {'source': 'LHE', 'date': self.tomorrow})
        self.assertNotIn('destination', result)

    def test_no_cities(self):
        result = extract_travel_info("I want a ticket for tomorrow")
        self.assertEqual(result, {'date': self.tomorrow})

    def test_misspelled_cities(self):
        result = extract_travel_info("I want to go from Laore to Krachi tomorrow")  # Misspelled Lahore & Karachi
        self.assertEqual(result, {'source': 'LHE', 'destination': 'KHI', 'date': self.tomorrow})

    def test_weird_phrasing(self):
        result = extract_travel_info("Need ticket Lahore Karachi tomorrow")
        # This may fail due to lack of 'from/to' cue
        self.assertIn('source', result)
        self.assertIn('destination', result)

    def test_only_one_city(self):
        result = extract_travel_info("Going to Sialkot")
        self.assertEqual(result, {'destination': 'SKT'})

    def test_city_with_multiple_words(self):
        result = extract_travel_info("from Dera Ghazi Khan to Islamabad on next Monday")
        self.assertEqual(result['source'], 'DEA')
        self.assertEqual(result['destination'], 'ISB')
        self.assertTrue('date' in result)

    # ❌ Nonexistent cities
    def test_unknown_city(self):
        result = extract_travel_info("from Narnia to Mordor tomorrow")
        self.assertEqual(result, {'date': self.tomorrow})

    def test_short_and_ambiguous(self):
        result = extract_travel_info("Multan tomorrow")
        self.assertEqual(result, {'source': 'MUX', 'date': self.tomorrow})  # Might assume Multan is source

    # ❌ Slippery time phrases
    def test_invalid_date(self):
        result = extract_travel_info("next blue moon")
        self.assertNotIn('date', result)

if __name__ == '__main__':
    unittest.main()
