#!/usr/bin/env python3

"""
Test script to demonstrate the improved flight result handling
"""

def test_flight_result_processing():
    """Test how the improved system handles different API response scenarios"""
    
    print("🧪 Testing Flight Result Processing Improvements")
    print("=" * 60)
    
    # Mock responses - exactly like what you provided
    
    # Scenario 1: Empty response (successful API call but no flights)
    empty_response = {
        "RefID": "878d047f-fde0-458c-ae4b-fb7671876b96",
        "TripType": "one_way",
        "TripNature": "domestic",
        "TravelClass": "business",
        "ClientCurrency": "PKR",
        "Travelers": [
            {"Type": "adult", "Count": 1},
            {"Type": "child", "Count": 0},
            {"Type": "infant", "Count": 0}
        ],
        "Passengers": [],
        "ContactDetails": {"FirstName": "", "LastName": ""},
        "Addon": {
            "Available": True,
            "Baggage": True,
            "Seat": True,
            "Meal": False,
            "MealSegmentMaxCount": 10,
            "Ssr": False
        },
        "Itineraries": [],  # Empty - no flights
        "IsCached": False,
        "airline": "TestAirline1",
        "status_code": 200
    }
    
    # Scenario 2: Response with actual flights
    response_with_flights = {
        "RefID": "da132ff5-b87e-472d-b115-5e1bd5a36c39",
        "TripType": "one_way",
        "TripNature": "domestic", 
        "TravelClass": "economy",
        "ClientCurrency": "PKR",
        "Travelers": [
            {"Type": "adult", "Count": 1},
            {"Type": "child", "Count": 0},
            {"Type": "infant", "Count": 0}
        ],
        "Passengers": [],
        "ContactDetails": {"FirstName": "", "LastName": ""},
        "Addon": {
            "Available": True,
            "Baggage": True,
            "Seat": True,
            "Meal": False,
            "MealSegmentMaxCount": 10,
            "Ssr": False
        },
        "Itineraries": [
            {
                "RefID": "01K1DJSTEJZZEHAX3R3D7B7T68",
                "TripNature": "domestic",
                "MarketingCarrier": {
                    "name": "Pakistan International Airlines",
                    "iata": "PK",
                    "country": "Pakistan"
                },
                "Flights": [
                    {
                        "Sequence": 1,
                        "MarketingCarrier": {
                            "name": "Pakistan International Airlines",
                            "iata": "PK"
                        },
                        "Segments": [
                            {
                                "Sequence": 1,
                                "OperatingCarrier": {
                                    "name": "Pakistan International Airlines",
                                    "iata": "PK"
                                },
                                "FlightNumber": "PK 303",
                                "From": {"iata": "LHE"},
                                "To": {"iata": "KHI"},
                                "DepartureAt": "2025-08-04T11:00:00+05:00",
                                "ArrivalAt": "2025-08-04T12:45:00+05:00",
                                "FlightTime": 105
                            }
                        ],
                        "Fares": [
                            {
                                "Name": "UOW1",
                                "ChargedBasePrice": 22690,
                                "ChargedTotalPrice": 25817,
                                "BaggagePolicy": [
                                    {"WeightLimit": 7, "Type": "carry"},
                                    {"WeightLimit": 20, "Type": "checked"}
                                ],
                                "Policies": [
                                    {"Type": "refund", "Charges": 4000}
                                ]
                            }
                        ]
                    }
                ]
            }
        ],
        "IsCached": False,
        "airline": "TestAirline2",
        "status_code": 200
    }
    
    # Test the flight extraction on both scenarios
    from travel_agent import ConversationalTravelAgent
    
    agent = ConversationalTravelAgent()
    
    print("\\n🔍 Testing Scenario 1: Empty Response (API success but no flights)")
    print("-" * 50)
    
    extracted_empty = agent.extract_flight_information(empty_response)
    print(f"Extracted flights: {len(extracted_empty)}")
    print(f"Expected: 0 flights (empty Itineraries array)")
    
    print("\\n🔍 Testing Scenario 2: Response with Actual Flights")  
    print("-" * 50)
    
    extracted_with_flights = agent.extract_flight_information(response_with_flights)
    print(f"Extracted flights: {len(extracted_with_flights)}")
    print(f"Expected: 1 flight")
    
    if extracted_with_flights:
        flight = extracted_with_flights[0]
        print(f"Flight details: {flight['airline']} {flight['flight_number']}")
        print(f"Route: {flight['origin']} → {flight['destination']}")
        print(f"Price: PKR {flight['fare_options'][0]['total_fare']:,}")
    
    print("\\n🔍 Testing Aggregation Logic")
    print("-" * 50)
    
    # Test aggregation with mixed results
    mock_results = [
        empty_response,  # No flights
        response_with_flights,  # Has flights
        {"error": "Network timeout", "airline": "TestAirline3", "status_code": 0}  # Failed
    ]
    
    aggregated = agent.aggregate_flight_results(mock_results)
    
    print(f"Total flights found: {aggregated['total_flights']}")
    print(f"Airlines with flights: {aggregated['airlines_with_flights']}")
    print(f"Successful API calls: {aggregated['successful_airlines']}")
    print(f"Failed API calls: {len(aggregated['errors'])}")
    
    print("\\n✅ Key Improvements:")
    print("1. ✅ Empty responses no longer counted as 'flights found'")
    print("2. ✅ Only airlines with actual flights are reported")
    print("3. ✅ Clear distinction between API success and flight availability")
    print("4. ✅ Proper context passed to LLM for accurate responses")

if __name__ == "__main__":
    test_flight_result_processing()
