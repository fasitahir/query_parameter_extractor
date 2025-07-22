from extract_parameters import extract_travel_info  # Replace with your actual script/module name

def run_test_cases():
    test_cases = [
        # One-way queries
        ("I want to fly from Lahore to Karachi today", {
            "source": "LHE", "destination": "KHI", "flight_type": "one_way"
        }),
        ("Book a flight to Islamabad from Multan on 5th August", {
            "source": "MUX", "destination": "ISB", "flight_type": "one_way"
        }),
        ("Travel to Skardu from Lahore on day after tomorrow", {
            "source": "LHE", "destination": "KDU", "flight_type": "one_way"
        }),
        ("Book a one-way ticket from GIL to LHE for tomorrow", {
            "source": "GIL", "destination": "LHE", "flight_type": "one_way"
        }),
        ("From Rawalpindi to Gilgit on 25th Dec", {
            "source": "ISB", "destination": "GIL", "flight_type": "one_way"
        }),

        # Return trip queries
        ("Book a return flight from Karachi to Lahore today and back on 25th July", {
            "source": "KHI", "destination": "LHE", "flight_type": "return"
        }),
        ("Need a round trip ticket from Islamabad to Sialkot on 10 August and back on 15 August", {
            "source": "ISB", "destination": "SKT", "flight_type": "return"
        }),
        ("Flight from Quetta to Peshawar and then back to Quetta", {
            "source": "UET", "destination": "PEW", "flight_type": "return"
        }),

        # Edge cases
        ("Flight to Karachi", {
            "destination": "KHI"
        }),
        ("I want to leave from Lahore", {
            "source": "LHE"
        }),
        ("I want to go to KHI from LHE today", {
            "source": "LHE", "destination": "KHI", "flight_type": "one_way"
        }),
        ("I want to go from Lahore to Lahore", {
            "source": "LHE"
        }),
        ("I want to go to panjgur and then to lahore", {
            "source": "LHE", "destination": "PJG", "flight_type": "return", "return_date": None
        }),
        ("Need a flight from sialkot to lahore", {  # Misspelled Lahore
            "source": "SKT", "destination": "LHE"
        }),
        ("Travel between Nawabshah and Rahim Yar Khan", {
            "source": "WNS", "destination": "RYK", "flight_type": "return"
        }),
                ("Book a flight from Karachi to Multan for 3rd September", {
            "source": "KHI", "destination": "MUX", "flight_type": "one_way"
        }),
        ("Need a return ticket to Peshawar from Lahore next Friday and back on Sunday", {
            "source": "LHE", "destination": "PEW", "flight_type": "return"
        }),
        ("Plan a one-way trip to Skardu on 15 August", {
            "destination": "KDU", "flight_type": "one_way"
        }),
        ("Going from LHE to KHI in 2 days", {
            "source": "LHE", "destination": "KHI", "flight_type": "one_way"
        }),
        ("Round trip please from Islamabad to Gilgit for tomorrow and back next Wednesday", {
            "source": "ISB", "destination": "GIL", "flight_type": "return"
        }),
        ("Get me a flight ticket", {
            # Not enough info to extract cities or dates
        }),
        ("Book a flight to ISLAMABAD", {
            "destination": "ISB", "flight_type": "one_way"
        }),
        ("Fly to Karachi from LHE day after tomorrow", {
            "source": "LHE", "destination": "KHI", "flight_type": "one_way"
        }),
        ("Return flight from Karachi to Lahore on the 30th", {
            "source": "KHI", "destination": "LHE", "flight_type": "return"
        }),
        ("Travel from Rahim Yar Khan to Nawabshah on 5th July and return on 10th July", {
            "source": "RYK", "destination": "WNS", "flight_type": "return"
        }),

    ]

    total = len(test_cases)
    passed = 0

    for i, (query, expected) in enumerate(test_cases, 1):
        result = extract_travel_info(query)
        print(f"\nTest {i}: '{query}'")
        print("Expected:", expected)
        print("Got     :", result)

        # Check if expected keys and values match
        match = True
        for key in expected:
            if key not in result or result[key] != expected[key]:
                match = False
                break

        if match:
            print("✅ Passed")
            passed += 1
        else:
            print("❌ Failed")

    print(f"\nPassed {passed}/{total} test cases.")

if __name__ == "__main__":
    run_test_cases()
