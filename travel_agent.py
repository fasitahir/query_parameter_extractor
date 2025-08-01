import json
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import os
from flight_tool import search_flights_with_context

# Load environment variables
load_dotenv()

def tool(func):
    """Decorator to mark functions as tools"""
    func.is_tool = True
    return func

# =============================================================================
# TOOLS SECTION - Each tool is a separate function with @tool decorator
# =============================================================================

@tool
def flight_search_and_extraction_tool(user_input: str, current_context: dict = None, search_mode: bool = False) -> dict:
    """
    Handle all flight-related functionality including travel information extraction and flight search.
    
    Use this tool for:
    - Extracting travel information from user's natural language input
    - Searching for flights when user wants to find flights or has confirmed travel details
    - Processing travel data like cities, dates, passenger counts, flight class, and preferences
    
    This tool automatically determines whether to extract information or search for flights
    based on the completeness of the travel information provided.
    
    Args:
        user_input (str): User's message containing travel information or search request
        current_context (dict): Existing booking context for better extraction/search
        search_mode (bool): If True, force flight search mode; if False, auto-determine
        
    Returns:
        dict: Extracted travel parameters, flight search results, or both with status
    """
    try:
        # Always extract travel information using contextual awareness - USE THE SAME LOGIC AS OLD AGENT
        from flight_tool import extract_travel_parameters
        
        # Start with current context to determine missing info for smart contextual query
        temp_context = current_context.copy() if current_context else {}
        
        # Calculate missing info for smart contextual query creation
        missing_info = []
        if not temp_context.get("source"):
            missing_info.append("departure_city")
        if not temp_context.get("destination"):
            missing_info.append("destination_city")
        if not temp_context.get("departure_date"):
            missing_info.append("departure_date")
        if temp_context.get("flight_type") == "return" and not temp_context.get("return_date"):
            missing_info.append("return_date")
        
        # Create contextual query with smart return date enhancement
        contextual_query = create_contextual_query(user_input, current_context, missing_info)
        # Pass None as current_context to prevent double contextualization in extract_travel_parameters
        extraction_result = extract_travel_parameters(contextual_query, None)
        
        # Start with current context
        updated_context = current_context.copy() if current_context else {}
        
        if extraction_result.get('status') == 'success':
            extracted_info = extraction_result.get('extracted_info', {})
            
            # Update context with newly extracted information - EXACTLY like old agent
            for key, value in extracted_info.items():
                if value is not None and value != '' and value != 'null':
                    # Special handling for passengers to avoid resetting
                    if key == 'passengers':
                        updated_context['passengers'] = value
                    elif key not in ['departure_date', 'return_date'] or value:
                        # Special handling for location codes
                        if key in ['source', 'destination'] and (not value or len(str(value)) < 2):
                            continue
                        updated_context[key] = value
        
        # Set defaults exactly like old agent - ONLY if not already set
        if not updated_context.get('passengers'):
            updated_context['passengers'] = {"adults": 1, "children": 0, "infants": 0}
        if not updated_context.get('flight_class'):
            updated_context['flight_class'] = 'economy'
        if not updated_context.get('flight_type'):
            updated_context['flight_type'] = 'one_way'
        
        # Recalculate missing info after extraction for final decision making
        final_missing_info = []
        if not updated_context.get("source"):
            final_missing_info.append("departure_city")
        if not updated_context.get("destination"):
            final_missing_info.append("destination_city")
        if not updated_context.get("departure_date"):
            final_missing_info.append("departure_date")
        if updated_context.get("flight_type") == "return" and not updated_context.get("return_date"):
            final_missing_info.append("return_date")
        
        # Determine if we should search for flights
        confirmation_words = ['yes', 'yeah', 'yep', 'correct', 'right', 'okay', 'ok', 'sure', 'confirm', 'search', 'find flights']
        is_confirmation = any(word in user_input.lower().strip() for word in confirmation_words)
        
        should_search = (
            search_mode or  # Forced search mode
            (not final_missing_info and is_confirmation) or  # User confirmed and we have complete info
            any(word in user_input.lower() for word in ['search', 'find flights', 'book', 'ready'])
        )
        
        if should_search and not final_missing_info:
            # Perform flight search
            search_result = search_flights_with_context(user_input, updated_context)
            
            return {
                "status": "success",
                "action": "flight_search",
                "message": "Flight search completed",
                "extracted_info": extraction_result.get('extracted_info', {}),
                "updated_context": updated_context,
                "flight_results": search_result.get("flight_results"),
                "formatted_display": search_result.get("formatted_display"),
                "search_type": search_result.get("search_type"),
                "missing_info": []
            }
        else:
            # Return extraction results with missing information
            return {
                "status": "success", 
                "action": "info_extraction",
                "message": "Travel information extracted",
                "extracted_info": extraction_result.get('extracted_info', {}),
                "updated_context": updated_context,
                "missing_info": final_missing_info
            }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Flight tool failed: {str(e)}",
            "action": "error",
            "extracted_info": {},
            "missing_info": [],
            "formatted_display": "Unable to process flight request at this time."
        }

def create_contextual_query(user_input: str, current_context: dict = None, missing_info: list = None) -> str:
    """Create a natural language contextual query exactly like the old agent did"""
    if not current_context:
        return user_input
    
    try:
        # Build natural language context from current booking info - EXACTLY like old agent
        natural_parts = []
        
        # Base travel information
        if current_context.get('source') and current_context.get('destination'):
            natural_parts.append(f"travel from {current_context['source']} to {current_context['destination']}")
        elif current_context.get('source'):
            natural_parts.append(f"travel from {current_context['source']}")
        elif current_context.get('destination'):
            natural_parts.append(f"go to {current_context['destination']}")
        
        # Passengers information - be specific about types EXACTLY like old agent
        passengers = current_context.get('passengers', {'adults': 1, 'children': 0, 'infants': 0})
        passenger_parts = []
        if passengers['adults'] > 0:
            if passengers['adults'] == 1:
                passenger_parts.append("1 adult")
            else:
                passenger_parts.append(f"{passengers['adults']} adults")
        if passengers['children'] > 0:
            if passengers['children'] == 1:
                passenger_parts.append("1 child")
            else:
                passenger_parts.append(f"{passengers['children']} children")
        if passengers['infants'] > 0:
            if passengers['infants'] == 1:
                passenger_parts.append("1 infant")
            else:
                passenger_parts.append(f"{passengers['infants']} infants")
        
        if passenger_parts:
            natural_parts.append(f"with {' and '.join(passenger_parts)}")
        
        # Date information
        if current_context.get('departure_date'):
            natural_parts.append(f"departing on {current_context['departure_date']}")
        
        if current_context.get('return_date'):
            natural_parts.append(f"returning on {current_context['return_date']}")
        
        # Travel class
        if current_context.get('flight_class'):
            class_name = current_context['flight_class'].replace('_', ' ')
            natural_parts.append(f"in {class_name} class")
        
        # Flight type
        if current_context.get('flight_type') == 'return':
            natural_parts.append("round trip")
        elif current_context.get('flight_type') == 'one_way':
            natural_parts.append("one way")
        
        # Airline preference
        if current_context.get('content_provider'):
            airline_name = current_context['content_provider'].replace('_', ' ').title()
            natural_parts.append(f"with {airline_name}")
        
        # Create natural language contextual query EXACTLY like old agent
        if natural_parts:
            base_context = " ".join(natural_parts)
            
            # SMART CONTEXT ENHANCEMENT: Add "return" prefix when collecting missing return date
            enhanced_user_input = user_input
            if (missing_info and 'return_date' in missing_info and 
                current_context.get('flight_type') == 'return' and 
                not current_context.get('return_date') and 
                current_context.get('departure_date')):
                return_indicators = ['return', 'back', 'returning', 'come back']
                if not any(indicator in user_input.lower() for indicator in return_indicators):
                    enhanced_user_input = f"return {user_input}"
                    print(f"Enhanced user input for return date: '{enhanced_user_input}'")
            
            contextual_query = f"{base_context}. Now {enhanced_user_input}"
            print(f"🔍 Contextual query created: {contextual_query}")
            return contextual_query
        
    except Exception as e:
        print(f"Error creating contextual query: {e}")
    
    return user_input

@tool
def get_bookme_info_tool(query: str) -> dict:
    """
    Provide information about BookMe services, policies, and company details.
    
    Use this tool when users ask about BookMe company, services, booking policies,
    payment methods, cancellation rules, or general company information.
    
    Args:
        query (str): User's question about BookMe
        
    Returns:
        dict: BookMe information and company details
    """
    # Placeholder for future BookMe information tool
    bookme_info = {
        "company": "BookMe is Pakistan's leading travel and entertainment platform",
        "services": ["Flight booking", "Hotel reservations", "Event tickets", "Bus tickets"],
        "payment_methods": ["Credit/Debit cards", "Bank transfer", "Mobile wallets"],
        "support": "24/7 customer support available",
        "cancellation": "Cancellation policies vary by airline and fare type"
    }
    
    # In the future, this could be enhanced with:
    # - Dynamic information retrieval
    # - Real-time policy updates
    # - Integration with BookMe's knowledge base
    
    return {
        "status": "success",
        "info": bookme_info,
        "message": "BookMe information retrieved successfully"
    }

# =============================================================================
# AGENT SECTION - Conversation management and tool orchestration
# =============================================================================

class ConversationalTravelAgent:
    """
    Conversational travel agent that manages user interactions and orchestrates tools.
    
    The agent handles conversation flow, maintains context, and decides which tools
    to use based on user input and conversation state.
    """
    
    def __init__(self):
        # Initialize LLM client
        try:
            self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            self.model_name = "meta-llama/llama-4-scout-17b-16e-instruct"
        except Exception as e:
            print(f"Warning: Failed to initialize Groq client: {e}")
            self.groq_client = None
            self.model_name = None
        
        # Conversation state
        self.conversation_history = []
        self.current_booking_info = {}
        
        # Available tools - automatically discovered by @tool decorator
        self.available_tools = self._discover_tools()

    def _discover_tools(self) -> dict:
        """Discover all available tools marked with @tool decorator"""
        tools = {}
        
        # Get all functions in the current module
        import sys
        current_module = sys.modules[__name__]
        
        for name in dir(current_module):
            obj = getattr(current_module, name)
            if callable(obj) and hasattr(obj, 'is_tool') and obj.is_tool:
                tools[name] = {
                    'function': obj,
                    'docstring': obj.__doc__ or 'No description available'
                }
        
        return tools

    def _select_appropriate_tool(self, user_input: str, conversation_context: str) -> str:
        """Use LLM to select the most appropriate tool based on user input and context"""
        try:
            # Build tool descriptions for the LLM
            tool_descriptions = ""
            for tool_name, tool_info in self.available_tools.items():
                tool_descriptions += f"- {tool_name}: {tool_info['docstring'].split('.')[0]}\n"
            
            prompt = f"""
                You are a tool selector for a travel agent. Based on the user's input and conversation context, select the most appropriate tool.

                Available tools:
                {tool_descriptions}

                Conversation context: {conversation_context}
                User input: "{user_input}"

                Rules:
                1. Use 'flight_search_and_extraction_tool' for ANY travel-related requests (searching flights, providing travel info, etc.)
                2. Use 'get_bookme_info_tool' when user asks about BookMe company, policies, or services
                3. If multiple tools could apply, choose the most relevant one
                4. Respond with ONLY the tool name, nothing else

                Selected tool:"""

            if self.groq_client and self.model_name:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_name,
                    temperature=0.1,  # Low temperature for consistent tool selection
                    max_tokens=50
                )
                selected_tool = chat_completion.choices[0].message.content.strip()
                
                # Validate the selected tool exists
                if selected_tool in self.available_tools:
                    return selected_tool
                else:
                    # Fallback to default tool
                    return 'flight_search_and_extraction_tool'
            else:
                # Fallback logic if LLM is not available
                if any(word in user_input.lower() for word in ['bookme', 'company', 'policy', 'cancel']):
                    return 'get_bookme_info_tool'
                else:
                    return 'flight_search_and_extraction_tool'
                    
        except Exception as e:
            print(f"Tool selection failed: {e}")
            return 'flight_search_and_extraction_tool'  # Default fallback

    # =============================================================================
    # CONVERSATION MANAGEMENT METHODS
    # =============================================================================

    def add_to_conversation(self, message, sender="user"):
        """Add message to conversation history"""
        self.conversation_history.append({
            "message": message,
            "sender": sender,
            "timestamp": datetime.now().isoformat()
        })

    def generate_conversational_response(self, user_input, context_info=None, tool_result=None):
        """Generate natural conversational responses using LLM"""
        try:
            # Build conversation context
            recent_conversation = "\n".join([
                f"{msg['sender'].title()}: {msg['message']}" 
                for msg in self.conversation_history[-4:]  # Last 4 messages for context
            ])
            
            current_info_summary = self._build_booking_info_summary()
            
            # Include tool result context if available
            tool_context = ""
            if tool_result:
                if tool_result.get('status') == 'success':
                    tool_context = f"Tool executed successfully. Result available for user."
                else:
                    tool_context = f"Tool execution had issues: {tool_result.get('message', 'Unknown error')}"

            prompt = f"""
You are a friendly, helpful travel agent having a natural conversation with a traveler. Be conversational, warm, and efficient.

Recent conversation:
{recent_conversation}

{current_info_summary}

Context: {context_info if context_info else "Continue natural conversation"}
Tool context: {tool_context}

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
9. NEVER mention booking confirmation, payment, or ticket issuance - you are only SEARCHING for flights
10. Use terms like "search for flights", "find options", "look for flights" - NOT "book", "confirm booking", or "process payment"
11. If user confirms details, say you'll search for flights, not process a booking

Respond naturally:
"""
            
            if self.groq_client and self.model_name:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_name,
                    temperature=0.7,
                    max_tokens=500,
                    top_p=0.9
                )
                return chat_completion.choices[0].message.content.strip()
            else:
                raise Exception("Groq client not initialized")
            
        except Exception as e:
            print(f"LLM generation failed: {e}")
            if "missing" in str(context_info).lower():
                return "I just need a couple more details to find your flights. What else can you tell me about your trip?"
            return "Tell me more about your travel plans!"

    def _build_booking_info_summary(self) -> str:
        """Build a summary of current booking information"""
        if not self.current_booking_info:
            return ""
            
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
        
        # Add passengers info properly
        passengers = self.current_booking_info.get('passengers', {'adults': 1, 'children': 0, 'infants': 0})
        total_passengers = passengers['adults'] + passengers['children'] + passengers['infants']
        info_parts.append(f"Passengers: {total_passengers} total ({passengers['adults']} adults, {passengers['children']} children, {passengers['infants']} infants)")
        
        if info_parts:
            return f"Current booking info: {', '.join(info_parts)}"
        return ""

    def update_booking_info_intelligently(self, extracted_info):
        """Update booking info while preserving existing information"""
        if not extracted_info:
            return
                
        # Special handling for passengers to avoid resetting
        if extracted_info.get('passengers'):
            self.current_booking_info['passengers'] = extracted_info['passengers']
        elif not self.current_booking_info.get('passengers'):
            self.current_booking_info['passengers'] = {"adults": 1, "children": 0, "infants": 0}
        
        # Update other fields - ONLY if the extracted value is not None/empty/null
        for key, value in extracted_info.items():
            if key != 'passengers' and value is not None and value != '' and value != 'null':
                if key in ['departure_date', 'return_date'] and not value:
                    continue
                if key in ['source', 'destination'] and (not value or len(str(value)) < 2):
                    continue
                self.current_booking_info[key] = value

    def identify_missing_information(self):
        """Identify what information is still needed"""
        missing = []
        
        if not self.current_booking_info.get("source"):
            missing.append("departure_city")
        if not self.current_booking_info.get("destination"):
            missing.append("destination_city")
        if not self.current_booking_info.get("departure_date"):
            missing.append("departure_date")
        # flight_class and flight_type are not required since we set defaults
        if self.current_booking_info.get("flight_type") == "return" and not self.current_booking_info.get("return_date"):
            missing.append("return_date")
            
        return missing

    # =============================================================================
    # MAIN CONVERSATION PROCESSING METHODS
    # =============================================================================

    def process_user_input_conversationally(self, user_input):
        """Process user input in a conversational manner - using old agent logic"""
        self.add_to_conversation(user_input, "user")
        
        try:
            # Use the flight tool with contextual extraction
            tool_result = self.available_tools['flight_search_and_extraction_tool']['function'](user_input, self.current_booking_info, False)
            
            # Update current booking info intelligently like the old agent
            if tool_result.get('status') == 'success':
                self.current_booking_info = tool_result.get('updated_context', self.current_booking_info)
            
            # Set default values for common fields if not specified (only if not already set) - like old agent
            if not self.current_booking_info.get("flight_class"):
                self.current_booking_info["flight_class"] = "economy"
            if not self.current_booking_info.get("flight_type"):
                self.current_booking_info["flight_type"] = "one_way"
            if not self.current_booking_info.get('passengers'):
                self.current_booking_info['passengers'] = {"adults": 1, "children": 0, "infants": 0}
                            
            # Determine what's missing and generate appropriate response
            missing_info = self.identify_missing_information()
            
            # Handle flight search result first
            if tool_result.get('action') == 'flight_search':
                # Flight search was successful - return the formatted response directly
                response = tool_result.get('formatted_display', 'Flight search completed')
                response_type = "search_complete"
            elif not missing_info:
                # All required information is available - move to confirmation
                response = self.generate_confirmation_summary()
                response_type = "confirmation"
            elif len(missing_info) <= 2:
                # Just a few things missing - ask conversationally
                response = self.generate_conversational_response(
                    user_input, 
                    f"Still need: {', '.join(missing_info)}",
                    tool_result
                )
                response_type = "gathering_info"
            else:
                # Need more basic info - provide guidance
                response = self.generate_conversational_response(
                    user_input,
                    "User is providing initial travel information",
                    tool_result
                )
                response_type = "initial_guidance"
                
            self.add_to_conversation(response, "assistant")
            
            return {
                "response": response,
                "type": response_type,
                "current_info": self.current_booking_info.copy(),
                "missing_info": missing_info,
                "tool_used": "flight_search_and_extraction_tool"
            }
            
        except Exception as e:
            error_response = "I'd love to help you with your travel plans! Could you tell me where you'd like to go and when?"
            self.add_to_conversation(error_response, "assistant")
            return {
                "response": error_response,
                "type": "error",
                "current_info": self.current_booking_info.copy(),
                "missing_info": [],
                "tool_used": None
            }

    def handle_modification_request(self, user_input):
        """Handle user requests to modify booking information"""
        self.add_to_conversation(user_input, "user")
        
        try:
            # Use the combined flight tool to extract new information
            tool_result = self.available_tools['flight_search_and_extraction_tool']['function'](user_input, self.current_booking_info, False)
            
            # Store old info for comparison
            old_info = self.current_booking_info.copy()
            
            # Update current booking info from tool result
            if tool_result.get('status') == 'success':
                self.current_booking_info = tool_result.get('updated_context', self.current_booking_info)
            
            # Generate response about what was changed
            changes_made = []
            if tool_result.get('status') == 'success':
                extracted_info = tool_result.get('extracted_info', {})
                for key, new_value in extracted_info.items():
                    if new_value and new_value != '' and new_value != 'null' and old_info.get(key) != new_value:
                        if key == 'passengers':
                            old_total = sum(old_info.get('passengers', {'adults': 1, 'children': 0, 'infants': 0}).values())
                            new_total = sum(new_value.values()) if isinstance(new_value, dict) else new_value
                            changes_made.append(f"passengers: {old_total} → {new_total}")
                        else:
                            old_val = old_info.get(key, 'not set')
                            changes_made.append(f"{key}: {old_val} → {new_value}")
            
            if changes_made:
                context = f"Changes made: {', '.join(changes_made)}"
            else:
                context = "User requested modification but no specific changes detected"
            
            response = self.generate_conversational_response(user_input, context, tool_result)
            self.add_to_conversation(response, "assistant")
            
            return {
                "response": response,
                "type": "modification",
                "current_info": self.current_booking_info.copy(),
                "missing_info": self.identify_missing_information(),
                "tool_used": "flight_search_and_extraction_tool"
            }
            
        except Exception as e:
            response = "I'd be happy to help you make changes! Could you tell me what you'd like to modify?"
            self.add_to_conversation(response, "assistant")
            return {
                "response": response,
                "type": "modification_error",
                "current_info": self.current_booking_info.copy(),
                "missing_info": [],
                "tool_used": None
            }

    def execute_flight_search_with_conversation(self):
        """Execute flight search using the combined flight tool"""
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
            search_start_msg = self.generate_search_start_message()
            self.add_to_conversation(search_start_msg, "assistant")
            
            # Execute the search using the combined flight tool (force search mode)
            search_result = self.available_tools['flight_search_and_extraction_tool']['function']("search for flights", self.current_booking_info, True)
            
            if search_result.get("status") == "success" and search_result.get("action") == "flight_search":
                # Generate conversational results presentation
                results_response = self.generate_flight_results_response(search_result)
                self.add_to_conversation(results_response, "assistant")
                
                return {
                    "response": f"{search_start_msg}\n\n{results_response}",
                    "type": "search_complete",
                    "status": "complete",
                    "flight_results": search_result.get("flight_results"),
                    "search_type": search_result.get("search_type"),
                    "tool_used": "flight_search_and_extraction_tool"
                }
            else:
                error_response = f"I encountered an issue while searching for flights: {search_result.get('message')}. Would you like me to try again?"
                self.add_to_conversation(error_response, "assistant")
                return {
                    "response": error_response,
                    "type": "search_error",
                    "status": "error",
                    "tool_used": "flight_search_and_extraction_tool"
                }
            
        except Exception as e:
            error_response = f"I encountered an issue while searching for flights: {str(e)}. Would you like me to try again?"
            self.add_to_conversation(error_response, "assistant")
            return {
                "response": error_response,
                "type": "search_error",
                "status": "error",
                "tool_used": None
            }

    def generate_search_start_message(self):
        """Generate an enthusiastic message about starting the search"""
        try:
            info = self.current_booking_info
            route = f"{info.get('source')} to {info.get('destination')}"
            
            prompt = f"""
Generate a brief, enthusiastic message that you're about to start searching for flights from {route}.

The message should:
1. Be excited and positive
2. Indicate you're starting the search process
3. Be very brief (1-2 sentences max)
4. Use terms like "searching", "looking", "finding" - NOT "booking" or "processing"

Examples: "Excellent! Let me search for the best flights for you now!" or "Perfect! Searching for your flights right away!"

Generate message:
"""
            
            if self.groq_client and self.model_name:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_name,
                    temperature=0.5,
                    max_tokens=100,
                    top_p=0.9
                )
                return chat_completion.choices[0].message.content.strip()
            else:
                raise Exception("Groq client not initialized")
            
        except Exception as e:
            return "Excellent! Let me search for the best flight options for you now!"

    def generate_flight_results_response(self, search_result):
        """Generate a conversational response about flight results"""
        try:
            # Use the formatted display from the search tool
            formatted_results = search_result.get("formatted_display", "Flight details not available")
            
            # Add a brief conversational intro
            if search_result.get("status") == "success":
                intro = "Great news! I found some flight options for you:"
            else:
                intro = "Here are the search results:"
            
            return f"{intro}\n\n{formatted_results}"
            
        except Exception as e:
            formatted_results = search_result.get("formatted_display", "Flight details not available")
            return f"I've completed your flight search! Here are the results:\n\n{formatted_results}"

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
            
            total_passengers = passengers['adults'] + passengers['children'] + passengers['infants']
            if total_passengers == 1:
                passenger_text = "for 1 person"
            elif passengers['children'] > 0 or passengers['infants'] > 0:
                passenger_text = f"for {total_passengers} passengers ({passengers['adults']} adults"
                if passengers['children'] > 0:
                    passenger_text += f", {passengers['children']} children"
                if passengers['infants'] > 0:
                    passenger_text += f", {passengers['infants']} infants"
                passenger_text += ")"
            else:
                passenger_text = f"for {passengers['adults']} adults"
            
            summary_parts.append(f"in {class_text} class {passenger_text}")
            
            # Optional airline
            airline_text = ""
            if info.get('content_provider'):
                airline_text = f" with {info['content_provider'].replace('_', ' ').title()}"
            
            summary = "Perfect! I have " + ", ".join(summary_parts) + airline_text + "."
            
            prompt = f"""
Create a brief, friendly confirmation message for this flight search:

{summary}

The message should:
1. Confirm the details naturally
2. Ask if they're ready to SEARCH for flights (not book - just search!)
3. Be warm but concise
4. Not repeat all the details again
5. Use words like "search", "find flights", "look for options" - NOT "book", "confirm booking", or "process payment"

Keep it short and conversational:
"""
            
            if self.groq_client and self.model_name:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_name,
                    temperature=0.6,
                    max_tokens=300,
                    top_p=0.9
                )
                return chat_completion.choices[0].message.content.strip()
            else:
                raise Exception("Groq client not initialized")
            
        except Exception as e:
            # Fallback to simple confirmation
            route = f"{info.get('source', '?')} to {info.get('destination', '?')}"
            date = info.get('departure_date', 'your chosen date')
            passengers = info.get('passengers', {'adults': 1, 'children': 0, 'infants': 0})
            total = passengers['adults'] + passengers['children'] + passengers['infants']
            passenger_text = f"{total} passenger{'s' if total > 1 else ''}"
            return f"Great! I have your {route} flight for {date} with {passenger_text}. Ready to search for the best options?"

    def reset_conversation(self):
        """Reset conversation state for new booking"""
        self.conversation_history = []
        self.current_booking_info = {}
        
        welcome_msg = "Hello! I'm your travel assistant, and I'm excited to help you find the perfect flight! ✈️ Tell me about your travel plans - where would you like to go?"
        self.add_to_conversation(welcome_msg, "assistant")
        return welcome_msg
