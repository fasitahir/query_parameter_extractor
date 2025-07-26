import json
import requests
from datetime import datetime
from extract_parameters import extract_travel_info, extract_flight_class, extract_flight_type, extract_cities, extract_airline
import google.generativeai as genai
from dotenv import load_dotenv
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ConversationalTravelAgent:
    def __init__(self):
        self.auth_url = "https://bookmesky.com/partner/api/auth/token"
        self.api_url = "https://bookmesky.com/air/api/search"
        self.username = os.getenv("BOOKME_SKY_USERNAME")
        self.password = os.getenv("BOOKME_SKY_PASSWORD")
        self.api_token = self.get_api_token()

        self.api_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_token}'
        }

        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Define popular airlines for multi-search
        self.popular_airlines = [
            "emirates", "qatar_airways", "etihad", "pia", "airblue", 
            "serene_air", "turkish_airlines", "lufthansa", "british_airways",
            "air_arabia", "flydubai", "saudia", "gulf_air"
        ]
        
        # Conversation context
        self.conversation_history = []
        self.current_booking_info = {}

    def get_api_token(self):
        """Fetch API token using credentials from environment variables"""
        try:
            payload = {
                "username": self.username,
                "password": self.password
            }
            response = requests.post(
                self.auth_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=10
            )

            if response.ok:
                token = response.json().get("Token")
                if token:
                    return token
                else:
                    raise Exception("Token not found in API response.")
            else:
                raise Exception(f"Auth failed: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"🔥 Error fetching token: {str(e)}")
            raise

    def add_to_conversation(self, message, sender="user"):
        """Add message to conversation history"""
        self.conversation_history.append({
            "message": message,
            "sender": sender,
            "timestamp": datetime.now().isoformat()
        })

    def generate_conversational_response(self, user_input, context_info=None):
        """Generate natural conversational responses using LLM"""
        try:
            # Build conversation context
            recent_conversation = "\n".join([
                f"{msg['sender'].title()}: {msg['message']}" 
                for msg in self.conversation_history[-4:]  # Last 4 messages for context
            ])
            
            current_info_summary = ""
            if self.current_booking_info:
                # Only show fields that have values
                info_parts = []
                if self.current_booking_info.get('source'):
                    info_parts.append(f"From: {self.current_booking_info['source']}")
                if self.current_booking_info.get('destination'):
                    info_parts.append(f"To: {self.current_booking_info['destination']}")
                if self.current_booking_info.get('departure_date'):
                    info_parts.append(f"Departure: {self.current_booking_info['departure_date']}")
                if self.current_booking_info.get('return_date'):
                    info_parts.append(f"Return: {self.current_booking_info['return_date']}")
                if self.current_booking_info.get('flight_class'):
                    info_parts.append(f"Class: {self.current_booking_info['flight_class']}")
                if self.current_booking_info.get('content_provider'):
                    info_parts.append(f"Airline: {self.current_booking_info['content_provider']}")
                
                if info_parts:
                    current_info_summary = f"Current booking info: {', '.join(info_parts)}"

            prompt = f"""
You are a friendly, helpful travel agent having a natural conversation with a traveler. Be conversational, warm, and efficient.

Recent conversation:
{recent_conversation}

{current_info_summary}

Context: {context_info if context_info else "Continue natural conversation"}

User just said: "{user_input}"

Rules:
1. Be natural and conversational - like talking to a friend
2. Don't repeat information unnecessarily 
3. If you have most details, smoothly ask for what's still needed
4. If confirming details, be concise and clear
5. Show enthusiasm but don't overdo it
6. Avoid repetitive questions about same information
7. If user changes something, acknowledge the change naturally
8. Keep responses focused and helpful

Respond naturally:
"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"LLM generation failed: {e}")
            # Provide better fallback responses
            if "missing" in str(context_info).lower():
                return "I just need a couple more details to find your flights. What else can you tell me about your trip?"
            return "Tell me more about your travel plans!"

    def process_user_input_conversationally(self, user_input):
        """Process user input in a conversational manner"""
        self.add_to_conversation(user_input, "user")
        
        try:
            # Extract travel information from the input
            extracted_info = extract_travel_info(user_input)
            
            # Update current booking info with any new information
            if extracted_info:
                # Handle changes smoothly
                old_info = self.current_booking_info.copy()
                self.current_booking_info.update({k: v for k, v in extracted_info.items() if v})
                
                # Set default values for common fields if not specified
                if not self.current_booking_info.get("flight_class"):
                    self.current_booking_info["flight_class"] = "economy"
                if not self.current_booking_info.get("flight_type"):
                    self.current_booking_info["flight_type"] = "one_way"
                if not self.current_booking_info.get("passengers"):
                    self.current_booking_info["passengers"] = {"adults": 1, "children": 0, "infants": 0}
            
            # Determine what's missing and generate appropriate response
            missing_info = self.identify_missing_information()
            
            if not missing_info:
                # All required information is available - move to confirmation
                response = self.generate_confirmation_summary()
                response_type = "confirmation"
            elif len(missing_info) <= 2:
                # Just a few things missing - ask conversationally
                response = self.generate_conversational_response(
                    user_input, 
                    f"Still need: {', '.join(missing_info)}"
                )
                response_type = "gathering_info"
            else:
                # Need more basic info - provide guidance
                response = self.generate_conversational_response(
                    user_input,
                    "User is providing initial travel information"
                )
                response_type = "initial_guidance"
                
            self.add_to_conversation(response, "assistant")
            
            return {
                "response": response,
                "type": response_type,
                "current_info": self.current_booking_info.copy(),
                "missing_info": missing_info
            }
            
        except Exception as e:
            error_response = "I'd love to help you with your travel plans! Could you tell me where you'd like to go and when?"
            self.add_to_conversation(error_response, "assistant")
            return {
                "response": error_response,
                "type": "error",
                "current_info": self.current_booking_info.copy(),
                "missing_info": []
            }

    def identify_missing_information(self):
        """Identify what information is still needed"""
        missing = []
        
        if not self.current_booking_info.get("source"):
            missing.append("departure_city")
        if not self.current_booking_info.get("destination"):
            missing.append("destination_city")
        if not self.current_booking_info.get("departure_date"):
            missing.append("departure_date")
        if not self.current_booking_info.get("flight_class"):
            missing.append("travel_class")
        if not self.current_booking_info.get("flight_type"):
            missing.append("trip_type")
        if self.current_booking_info.get("flight_type") == "return" and not self.current_booking_info.get("return_date"):
            missing.append("return_date")
        # Airline is now optional - removed from required fields
            
        return missing

    def generate_confirmation_summary(self):
        """Generate a natural confirmation summary"""
        try:
            info = self.current_booking_info
            
            # Build a natural, concise summary
            summary_parts = []
            
            # Basic trip info
            if info.get('source') and info.get('destination'):
                trip_type = "round-trip" if info.get('flight_type') == 'return' else "one-way"
                summary_parts.append(f"{trip_type} from {info['source']} to {info['destination']}")
            
            # Date
            if info.get('departure_date'):
                summary_parts.append(f"on {info['departure_date']}")
            
            # Add return date if applicable
            if info.get('return_date'):
                summary_parts.append(f"returning {info['return_date']}")
            
            # Class and passengers
            passengers = info.get('passengers', {'adults': 1, 'children': 0, 'infants': 0})
            class_text = info.get('flight_class', 'economy').replace('_', ' ')
            
            passenger_count = passengers['adults']
            if passengers['children'] > 0 or passengers['infants'] > 0:
                passenger_count += passengers['children'] + passengers['infants']
                passenger_text = f"for {passenger_count} passengers"
            else:
                passenger_text = "for 1 adult" if passenger_count == 1 else f"for {passenger_count} adults"
            
            summary_parts.append(f"in {class_text} class {passenger_text}")
            
            # Optional airline
            airline_text = ""
            if info.get('content_provider'):
                airline_text = f" with {info['content_provider'].replace('_', ' ').title()}"
            
            summary = "Perfect! I have " + ", ".join(summary_parts) + airline_text + "."
            
            prompt = f"""
Create a brief, friendly confirmation message for this flight booking:

{summary}

The message should:
1. Confirm the details naturally
2. Ask if they're ready to search or want to change anything
3. Be warm but concise
4. Not repeat all the details again

Keep it short and conversational:
"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            # Fallback to simple confirmation
            route = f"{info.get('source', '?')} to {info.get('destination', '?')}"
            date = info.get('departure_date', 'your chosen date')
            return f"Great! I have your {route} flight for {date}. Ready to search for the best options?"

    def handle_modification_request(self, user_input):
        """Handle user requests to modify booking information"""
        self.add_to_conversation(user_input, "user")
        
        try:
            # Extract any new information from the modification request
            extracted_info = extract_travel_info(user_input)
            
            # Update current booking info
            if extracted_info:
                old_info = self.current_booking_info.copy()
                self.current_booking_info.update({k: v for k, v in extracted_info.items() if v})
                
                # Generate response about what was changed
                changes_made = []
                for key, new_value in extracted_info.items():
                    if new_value and old_info.get(key) != new_value:
                        changes_made.append(f"{key}: {old_info.get(key, 'not set')} → {new_value}")
                
                if changes_made:
                    context = f"Changes requested: {', '.join(changes_made)}"
                else:
                    context = "User wants to modify booking but no specific changes detected"
            else:
                context = "User wants to modify something but specifics unclear"
            
            response = self.generate_conversational_response(user_input, context)
            self.add_to_conversation(response, "assistant")
            
            return {
                "response": response,
                "type": "modification",
                "current_info": self.current_booking_info.copy(),
                "missing_info": self.identify_missing_information()
            }
            
        except Exception as e:
            response = "I'd be happy to help you make changes! Could you tell me what you'd like to modify?"
            self.add_to_conversation(response, "assistant")
            return {
                "response": response,
                "type": "modification_error",
                "current_info": self.current_booking_info.copy(),
                "missing_info": []
            }

    def execute_flight_search_with_conversation(self):
        """Execute flight search with conversational feedback"""
        try:
            # Validate all required information is present
            missing = self.identify_missing_information()
            if missing:
                response = f"I still need a bit more information before I can search: {', '.join(missing)}. Could you help me with those details?"
                self.add_to_conversation(response, "assistant")
                return {
                    "response": response,
                    "type": "missing_info",
                    "status": "incomplete"
                }
            
            # Generate enthusiastic search start message
            search_start_msg = self.generate_conversational_response(
                "ready to search", 
                "User confirmed they want to proceed with flight search"
            )
            self.add_to_conversation(search_start_msg, "assistant")
            
            # Execute the actual search
            payload = self.format_api_payload(self.current_booking_info)
            if "error" in payload:
                error_response = f"Oops! There seems to be an issue with the booking details: {payload['error']}. Could you help me correct this?"
                self.add_to_conversation(error_response, "assistant")
                return {
                    "response": error_response,
                    "type": "error",
                    "status": "error"
                }
            
            # Perform the search
            specific_airline = self.current_booking_info.get("content_provider")
            search_results = self.search_flights_parallel(payload, specific_airline)
            
            # Process results
            if specific_airline:
                flight_results = search_results[0] if search_results else {"error": "No results"}
                search_type = "single_airline"
            else:
                flight_results = self.aggregate_flight_results(search_results)
                search_type = "multi_airline"
            
            # Generate conversational results presentation
            results_response = self.generate_flight_results_response(flight_results, search_type)
            self.add_to_conversation(results_response, "assistant")
            
            return {
                "response": f"{search_start_msg}\n\n{results_response}",
                "type": "search_complete",
                "status": "complete",
                "flight_results": flight_results,
                "search_type": search_type
            }
            
        except Exception as e:
            error_response = f"I encountered an issue while searching for flights: {str(e)}. Would you like me to try again?"
            self.add_to_conversation(error_response, "assistant")
            return {
                "response": error_response,
                "type": "search_error",
                "status": "error"
            }

    def generate_flight_results_response(self, flight_results, search_type):
        """Generate a conversational response about flight results"""
        try:
            if search_type == "single_airline":
                if isinstance(flight_results, dict) and "error" in flight_results:
                    return f"I wasn't able to find flights with your preferred airline right now. {flight_results['error']} Would you like me to search across other airlines instead?"
                
                # Format single airline results
                context = f"Single airline search completed. Results type: {type(flight_results)}"
                
            else:
                # Multi-airline results
                total_flights = flight_results.get('total_flights', 0) if isinstance(flight_results, dict) else 0
                successful_airlines = flight_results.get('successful_airlines', 0) if isinstance(flight_results, dict) else 0
                
                if total_flights == 0:
                    context = f"Multi-airline search completed but no flights found. {successful_airlines} airlines responded successfully."
                else:
                    context = f"Multi-airline search completed successfully. Found {total_flights} flights across {successful_airlines} airlines."
            
            # Generate natural response about results
            prompt = f"""
Flight search has been completed. Context: {context}

Generate a conversational, helpful response that:
1. Presents the flight search results in a natural way
2. Highlights key findings or best options if available
3. Mentions any issues or alternatives if no flights found
4. Maintains a helpful, professional tone
5. Offers next steps or asks what the user would prefer

Keep it conversational and informative.
"""
            
            response = self.model.generate_content(prompt)
            llm_response = response.text
            
            # Combine with formatted flight data
            formatted_results = self.format_flight_results_for_display(flight_results, search_type)
            
            return f"{llm_response}\n\n{formatted_results}"
            
        except Exception as e:
            return f"I've completed your flight search! Here are the results:\n\n{self.format_flight_results_for_display(flight_results, search_type)}"

    def reset_conversation(self):
        """Reset conversation state for new booking"""
        self.conversation_history = []
        self.current_booking_info = {}
        
        welcome_msg = "Hello! I'm your travel assistant, and I'm excited to help you find the perfect flight! ✈️ Tell me about your travel plans - where would you like to go?"
        self.add_to_conversation(welcome_msg, "assistant")
        return welcome_msg

    # Include all the original technical methods (search_flights_parallel, format_api_payload, etc.)
    # These remain the same as they handle the API interactions
    
    def format_api_payload(self, info, airline=None):
        """Format the extracted information into API payload"""
        try:
            # Build locations
            locations = []
            if info.get("source"):
                locations.append({"IATA": info["source"], "Type": "airport"})
            if info.get("destination"):
                locations.append({"IATA": info["destination"], "Type": "airport"})
            
            # Build traveling dates
            traveling_dates = []
            if info.get("departure_date"):
                traveling_dates.append(info["departure_date"])
            if info.get("return_date"):
                traveling_dates.append(info["return_date"])
            
            # Build travelers
            passengers = info.get("passengers", {"adults": 1, "children": 0, "infants": 0})
            travelers = []
            if passengers["adults"] > 0:
                travelers.append({"Type": "adult", "Count": passengers["adults"]})
            if passengers["children"] > 0:
                travelers.append({"Type": "child", "Count": passengers["children"]})
            if passengers["infants"] > 0:
                travelers.append({"Type": "infant", "Count": passengers["infants"]})
            
            # Build payload
            payload = {
                "Locations": locations,
                "Currency": "PKR",
                "TravelClass": info.get("flight_class", "economy"),
                "TripType": info.get("flight_type", "one_way"),
                "TravelingDates": traveling_dates,
                "Travelers": travelers
            }
            
            # Add content provider
            content_provider = airline or info.get("content_provider")
            if content_provider:
                payload["ContentProvider"] = content_provider
                
            return payload
            
        except Exception as e:
            return {"error": f"Failed to format payload: {str(e)}"}
    
    def search_single_airline(self, payload, airline_name=None):
        """Search flights for a single airline"""
        try:
            search_payload = payload.copy()
            if airline_name:
                search_payload["ContentProvider"] = airline_name
            
            response = requests.post(
                self.api_url,
                headers=self.api_headers,
                json=search_payload,
                timeout=30
            )            
            if response.status_code == 200:
                result = response.json()
                result["airline"] = airline_name or "All Airlines"
                result["search_payload"] = search_payload
                return result
            else:
                error_msg = f"API request failed with status {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        if "message" in error_data:
                            error_msg += f": {error_data['message']}"
                        elif "error" in error_data:
                            error_msg += f": {error_data['error']}"
                    except:
                        error_msg += f": {response.text[:200]}"
                
                return {
                    "error": error_msg,
                    "status_code": response.status_code,
                    "airline": airline_name or "All Airlines"
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Network error: {str(e)}", 
                "airline": airline_name or "All Airlines"
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}", 
                "airline": airline_name or "All Airlines"
            }
    
    def search_flights_parallel(self, payload, specific_airline=None):
        """Search flights across multiple airlines in parallel or single airline"""
        
        if specific_airline:
            print(f"🔍 Searching flights for {specific_airline}...")
            return [self.search_single_airline(payload, specific_airline)]
        
        print(f"🔍 Searching flights across {len(self.popular_airlines)} airlines...")
        
        results = []
        successful_searches = 0
        failed_searches = 0
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_airline = {
                executor.submit(self.search_single_airline, payload, airline): airline 
                for airline in self.popular_airlines
            }
            
            for future in as_completed(future_to_airline):
                airline = future_to_airline[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if "error" in result:
                        failed_searches += 1
                        print(f"❌ {airline}: {result.get('error', 'Unknown error')}")
                    else:
                        successful_searches += 1
                        print(f"✅ {airline}: Search completed successfully")
                        
                except Exception as e:
                    failed_searches += 1
                    print(f"❌ {airline}: Exception occurred - {str(e)}")
                    results.append({
                        "error": f"Thread execution failed: {str(e)}",
                        "airline": airline
                    })
        
        print(f"📊 Search Summary: {successful_searches} successful API calls, {failed_searches} failed")
        return results
    
    def aggregate_flight_results(self, results):
        """Aggregate and sort flight results from multiple airlines"""
        all_flights = []
        errors = []
        successful_results = []
        
        for result in results:
            airline = result.get("airline", "Unknown")
            
            if "error" in result:
                errors.append({
                    "airline": airline,
                    "error": result["error"]
                })
                continue
            
            successful_results.append(result)
            
            flights = None
            if "data" in result and result["data"]:
                flights = result["data"]
            elif "flights" in result and result["flights"]:
                flights = result["flights"]
            elif "results" in result and result["results"]:
                flights = result["results"]
            elif "itineraries" in result and result["itineraries"]:
                flights = result["itineraries"]
            else:
                if isinstance(result, dict) and any(key in result for key in ["price", "cost", "totalPrice", "fare"]):
                    flights = [result]
            
            if flights:
                if isinstance(flights, list):
                    for flight in flights:
                        if isinstance(flight, dict):
                            flight["source_airline"] = airline
                            all_flights.append(flight)
                elif isinstance(flights, dict):
                    flights["source_airline"] = airline
                    all_flights.append(flights)
        
        try:
            def get_price(flight):
                price_fields = ["price", "totalPrice", "cost", "fare", "amount"]
                for field in price_fields:
                    if field in flight and flight[field] is not None:
                        try:
                            return float(flight[field])
                        except (ValueError, TypeError):
                            continue
                return 999999
            
            all_flights.sort(key=get_price)
        except Exception as e:
            print(f"Warning: Could not sort flights by price: {e}")
        
        return {
            "flights": all_flights[:50],
            "total_flights": len(all_flights),
            "successful_airlines": len(successful_results),
            "successful_results": successful_results,
            "errors": errors
        }
    
    def format_flight_results_for_display(self, flight_results, search_type="multi_airline"):
        """Format flight results for better display to user"""
        try:
            if search_type == "single_airline":
                if isinstance(flight_results, list) and len(flight_results) > 0:
                    result = flight_results[0]
                    if "error" in result:
                        return f"❌ Search Error: {result['error']}"
                    
                    flights_data = result.get('data', result.get('flights', result))
                    airline_name = result.get('airline', 'Unknown Airline')
                    
                    if not flights_data or (isinstance(flights_data, list) and len(flights_data) == 0):
                        return f"No flights found for {airline_name}."
                    
                    return self.format_single_airline_display(flights_data, airline_name)
                else:
                    return "No flight results received."
            
            else:
                if not flight_results or not isinstance(flight_results, dict):
                    return "No flight results received from the search."
                
                total_flights = flight_results.get('total_flights', 0)
                successful_airlines = flight_results.get('successful_airlines', 0)
                flights = flight_results.get('flights', [])
                errors = flight_results.get('errors', [])
                
                if total_flights == 0:
                    if successful_airlines > 0:
                        return f"I searched {successful_airlines + len(errors)} airlines successfully, but unfortunately no flights are available for your specific criteria. You might want to try different dates or nearby airports."
                    else:
                        return "I wasn't able to connect to the airline systems right now. Please try again in a few minutes."
                
                return self.format_multi_airline_display(flights, total_flights, successful_airlines, errors)
                
        except Exception as e:
            return f"I found some flight options but had trouble formatting them. The search was successful though!"

    def format_single_airline_display(self, flights_data, airline_name):
        """Format single airline flight data for display"""
        try:
            display_text = f"Here are the available flights with {airline_name}:\n\n"
            
            if isinstance(flights_data, dict):
                segments = flights_data.get('segments', flights_data.get('itineraries', [flights_data]))
            elif isinstance(flights_data, list):
                segments = flights_data
            else:
                segments = [flights_data]
            
            for i, flight in enumerate(segments[:5], 1):
                display_text += f"✈️ **Option {i}:**\n"
                
                price = flight.get('price', flight.get('totalPrice', flight.get('cost', 'N/A')))
                departure_time = flight.get('departureTime', flight.get('departure', 'N/A'))
                arrival_time = flight.get('arrivalTime', flight.get('arrival', 'N/A'))
                duration = flight.get('duration', flight.get('flightDuration', 'N/A'))
                
                display_text += f"   💰 Price: PKR {price}\n"
                display_text += f"   🛫 Departure: {departure_time}\n"
                display_text += f"   🛬 Arrival: {arrival_time}\n"
                display_text += f"   ⏱️ Duration: {duration}\n\n"
                
            return display_text
            
        except Exception as e:
            return f"Found flights with {airline_name} but couldn't display all details."

    def format_multi_airline_display(self, flights, total_flights, successful_airlines, errors):
        """Format multi-airline flight data for display"""
        try:
            display_text = f"Great news! I found {total_flights} flight options across {successful_airlines} airlines:\n\n"
            
            if not flights:
                return "I completed the search but couldn't retrieve the detailed flight information."
            
            airline_groups = {}
            for flight in flights[:10]:
                airline = flight.get('source_airline', flight.get('airline', 'Unknown'))
                if airline not in airline_groups:
                    airline_groups[airline] = []
                airline_groups[airline].append(flight)
            
            for airline, airline_flights in airline_groups.items():
                display_text += f"✈️ **{airline.upper().replace('_', ' ')}** ({len(airline_flights)} options):\n"
                
                for i, flight in enumerate(airline_flights[:3], 1):
                    price = flight.get('price', flight.get('totalPrice', flight.get('cost', 'N/A')))
                    departure_time = flight.get('departureTime', flight.get('departure', 'N/A'))
                    arrival_time = flight.get('arrivalTime', flight.get('arrival', 'N/A'))
                    duration = flight.get('duration', flight.get('flightDuration', 'N/A'))
                    
                    display_text += f"   💰 PKR {price} | 🛫 {departure_time} → 🛬 {arrival_time} | ⏱️ {duration}\n"
                
                display_text += "\n"
            
            if errors and len(errors) > 0:
                display_text += f"(Note: {len(errors)} airlines had temporary connection issues)\n"
            
            return display_text
            
        except Exception as e:
            return f"Found {total_flights} flights but had some display issues. The search was successful!"