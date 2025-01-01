import asyncio
from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatEvent
from twitchAPI.helper import first
from twitchAPI.type import AuthScope
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.eventsub.websocket import EventSubWebsocket
from ollama import AsyncClient
from duckduckgo_search import AsyncDDGS
import json
import os
import argparse
import re
from datetime import datetime
import multiprocessing

class Bot:
    MAX_HISTORY_SIZE = 100  # Maximum number of messages to keep in history
    
    def __init__(self, history_file=None, config_file=None, model="llama3.2:3b-instruct-q4_0"):

        self.config_file = config_file

        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                self.app_id = config_data['login_template'].get('app_id')
                self.app_secret = config_data['login_template'].get('app_secret')
                self.channel_name = config_data['login_template'].get('channel_name')
                self.streamer_name = config_data['login_template'].get('streamer_name', self.channel_name)
                self.bot_name = config_data['login_template'].get('bot_name', 'SLM_Bot')
                self.category_change_template = config_data['category_change_template'].get('category_changed_text')
                self.empty_category_template = config_data['category_change_template'].get('empty_category_text')
                print("Loaded login credentials from config file")
            except Exception as e:
                print(f"Error loading login file: {e}")
                self._prompt_credentials()
        else:
            self._prompt_credentials()

        self.llm = AsyncClient()
        self.model = model
        self.chat_history = []
        self.history_file = history_file

        # This is updated automatically! Do not set this manually.
        self.current_category = ""
        self.prompt = ""
        
        # Load chat history if file specified and exists
        if self.history_file and os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.chat_history = json.load(f)
                print(f"Loaded {len(self.chat_history)} messages from history")
            except Exception as e:
                print(f"Error loading chat history: {e}")
                self.chat_history = []
        
        self.user_scope = [
            AuthScope.CHAT_READ,
            AuthScope.CHAT_EDIT,
            AuthScope.CHANNEL_BOT,
            AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
            AuthScope.MODERATOR_READ_FOLLOWERS  # Added for EventSub
        ]

        self.twitch = None
        self.chat = None
        self.eventsub = None
        self.user_id = None

    def _prompt_credentials(self):
        """Prompt user for Twitch credentials if not loaded from file."""
        self.app_id = input("Enter your Twitch application ID: ")
        self.app_secret = input("Enter your Twitch application secret: ")
        self.channel_name = input("Enter your channel name here: ")
        self.streamer_name = input("Enter your streamer's name here (leave blank for channel name): ")
        if not self.streamer_name:
            self.streamer_name = self.channel_name

    async def update_system_prompt(self):
        # Load custom prompt from file if specified
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    template = json.load(f).get('prompt_template')
                template = template.format(
                    bot_name=self.bot_name,
                    streamer_name=self.streamer_name,
                    current_category=self.current_category,
                    chat_history=self.chat_history
                )
                self.prompt = template.format(
                    streamer_name=self.streamer_name,
                    current_category=self.current_category
                )
                print("Loaded custom prompt template")
            except Exception as e:
                print(f"Error loading prompt template: {e}")
                self._use_default_prompt()
        else:
            self._use_default_prompt()

    def _use_default_prompt(self):
        """Set the default system prompt."""
        self.prompt = f"""
        You are {self.bot_name}, a chatbot on a Twitch stream alongside your host.
        You are a helpful assistant that chats with the stream chat, answers questions about the streamer's game, etc.
        You should respond to recent messages in the chat history with your response content only.
        Do not respond with anything other than your text reply.

        The streamer's name is {self.streamer_name}.
        The current game is {self.current_category}. If the stream is offline, feel free to chat still.

        Example Chat:
            viewer123: Hello bot!
            {self.bot_name}: Hi there! Welcome to the stream! What game are you watching today?
            viewer123: {self.streamer_name} is playing {self.current_category} today.

        DO NOT use any tool calls unless necessary. ONLY use tool calls when a user specifically asks. DO NOT search the internet unecessarily.

        The conversation history is as follows:
        {self.chat_history}
        """

    async def on_ready(self, ready_event: EventData):
        """Called when the chat connection is ready."""
        try:
            await self.chat.join_room(self.channel_name)
            print(f'Connected to {self.channel_name}\'s chat')

            # Get current game from Twitch API
            try:
                stream = await first(self.twitch.get_streams(user_login=self.streamer_name))
                if stream:
                    self.current_category = stream.game_name
                    print(f"Detected game: {self.current_category}")
                else:
                    self.current_category = "[Stream Offline]"
                    print("Stream appears to be offline")
            except Exception as e:
                self.current_category = "[Unknown Category]"
                print(f"Could not detect current category: {e}")

            # Update system prompt with new game information
            await self.update_system_prompt()

        except Exception as e:
            print(f'Failed to connect to {self.channel_name}\'s chat: {e}')

    async def save_history(self):
        """Save chat history to file if history_file is specified."""
        if self.history_file:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
                with open(self.history_file, 'w') as f:
                    json.dump(self.chat_history, f, indent=2)
            except Exception as e:
                print(f"Error saving chat history: {e}")

    async def null_tool_call(self):
        return ''

    async def search_internet(self, query):
        results = await AsyncDDGS().atext(query, max_results=3)
        return results

    async def get_current_time(self):
        return datetime.now().isoformat()

    def _get_available_tools(self):
        return [
            {
                'type': 'function',
                'function': {
                    'name': 'respond_to_user',
                    'description': 'Skips the tool call and sends a message to the user.',
                    'parameters': {
                        'type': 'object',
                        'properties': {},
                    },
                    'required': []
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'search_internet',
                    'description': 'Search the internet using DuckDuckGo. Returns up to 3 results. To be used only when a chat user asks for an internet search.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'query': {
                                'type': 'string',
                                'description': 'The query to search for.'
                            }
                        },
                    },
                    'required': ['query']
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'get_current_time',
                    'description': 'Returns the current time in UTC. To be used only when a chat user asks for the current time.',
                    'parameters': {
                        'type': 'object',
                        'properties': {},
                    },
                    'required': []
                }
            }
        ]

    async def _get_llm_response(self, llm_results):
        # Get response from LLM
        try:
            response = await self.llm.chat(
                model=self.model, 
                messages=[{'role': 'system', 'content': self.prompt}] + self.chat_history,
                tools = self._get_available_tools(),
                options={
                    'temperature': 0.2
                }
            )
            response_text = response['message']['content']
            try:
                response_tools = response['message']['tool_calls']
            except KeyError:
                response_tools = []
        except Exception as e:
            print(f"Error connecting to LLM: {e}")
            response_text = 'There was an error connecting to the LLM. Please try again later.'
            response_tools = []

        llm_results['response_text'] = response_text
        llm_results['response_tools'] = response_tools
        return response_text, response_tools

    async def check_message(self, msg: str):
        """Checks the LLM generated message content with another LLM to:
        1. Ensure the message is not harmful or illegal,
        2. Make sure the message is actually a message, and not JSON,
        3. Check that no other errors are present. """

        check_prompt = f"""
        You are a message-checking system for an AI chatbot.
        Your purpose is to ensure that the messages the chatbot sends are not harmful, illegal, or offensive.
        You also ensure that the message is actually a text message, and not random JSON tool calls.
        Remember, the message is a chatbot message, so the only content should be a normal text message.

        If the message is OK to send, respond with {{ "accepted": true }}. Otherwise, respond with {{ "accepted": false }}.
        Respond only with valid JSON.
        """

        try:
            response = await self.llm.chat(
                model=self.model, 
                messages=[{'role': 'system', 'content': check_prompt}, {'role': 'user', 'content': msg}],
                options={
                    'temperature': 0.2
                }
            )
            response_text = response['message']['content']
            print(f"Checked message: {response_text}")
        except Exception as e:
            print(f"Error checking message: {e}")
            return False

        try:
            response = json.loads(response_text)
            return response['accepted']
        except Exception as e:
            print(f"Error checking message: {e}")
            return False

    async def on_message(self, msg: ChatMessage):
        """Called when a message is received in chat."""

        if not msg.text.startswith('!ai'):
            return

        msg.text = msg.text[4:].strip()

        print(f"Received message from {msg.user.name}: {msg.text}")

        # Add user message to chat history
        self.chat_history.append({
            'role': 'user', 
            'content': f"{msg.user.name}: {msg.text}"
        })
        
        # Keep only the most recent messages
        if len(self.chat_history) > self.MAX_HISTORY_SIZE:
            self.chat_history = self.chat_history[-self.MAX_HISTORY_SIZE:]

        # Get response from LLM
        def generate_response(llm_results):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_text, response_tools = loop.run_until_complete(self._get_llm_response(llm_results))
            llm_results['response_text'] = response_text
            llm_results['response_tools'] = response_tools

        llm_results = multiprocessing.Manager().dict()
        response_process = multiprocessing.Process(target=generate_response, args=(llm_results,))
        response_process.start()
        response_process.join(timeout=30)  # Wait for 30 seconds

        if response_process.is_alive():
            response_process.terminate()  # Terminate the process if it exceeds the time limit
            response_text = "Sorry, the generation took too long. Please try again later."
            response_tools = []
        else:
            response_text = llm_results['response_text']
            response_tools = llm_results['response_tools']

        print(f"Generated response: {response_text}")
        print(f"Generated tools: {response_tools}")

        if response_tools:
            for tool in response_tools:
                if tool['function']['name'] == 'respond_to_user':
                    tool_response = await self.null_tool_call()
                    self.chat_history.append({
                        'role': 'tool',
                        'content': f"Null tool call was used."
                    })
                if tool['function']['name'] == 'search_internet':
                    query = tool['function']['arguments']['query']
                    try:
                        tool_response = await self.search_internet(query)
                        self.chat_history.append({
                            'role': 'tool',
                            'content': f"Tool {tool['function']['name']} returned {len(tool_response)} results. Results: {tool_response}"
                        })
                    except Exception as e:
                        print(f"Error searching internet: {e}")
                        self.chat_history.append({
                            'role': 'tool',
                            'content': f"Tool {tool['function']['name']} returned an error: {e}"
                        })
                if tool['function']['name'] == 'get_current_time':
                    try:
                        tool_response = await self.get_current_time()
                        self.chat_history.append({
                            'role': 'tool',
                            'content': f"Tool {tool['function']['name']} returned {tool_response}"
                        })
                    except Exception as e:
                        print(f"Error getting current time: {e}")
                        self.chat_history.append({
                            'role': 'tool',
                            'content': f"Tool {tool['function']['name']} returned an error: {e}"
                        })
            response_text, _ = await self._get_llm_response(llm_results)

        if len(response_text) == 0:
            response_text = 'There was an error processing your request. Please try again later.'

        response_text = re.sub(rf"^{re.escape(self.bot_name)}:", "", response_text, flags=re.MULTILINE)

        print(f"Sending response: {response_text}")

        # Check if message is OK to send
        if not await self.check_message(response_text):
            response_text = 'There was an error processing your request. Please try again later.'
            response_tools = []
        
        # Send response to chat
        await self.chat.send_message(self.channel_name, response_text)
        
        # Add bot's response to chat history
        self.chat_history.append({
            'role': 'assistant',
            'content': f"{self.bot_name}: {response_text}"
        })
        
        # Keep history within size limit after adding response
        if len(self.chat_history) > self.MAX_HISTORY_SIZE:
            self.chat_history = self.chat_history[-self.MAX_HISTORY_SIZE:]
        
        # Save history after each message if file is specified
        await self.save_history()

    async def setup_eventsub(self):
        """Set up EventSub for stream updates."""
        try:
            # Get the broadcaster's user ID
            user = await first(self.twitch.get_users(logins=[self.streamer_name]))
            self.user_id = user.id
            
            # Initialize EventSub
            self.eventsub = EventSubWebsocket(self.twitch)
            self.eventsub.start()
            
            # Subscribe to channel update events
            await self.eventsub.listen_channel_update_v2(
                broadcaster_user_id=self.user_id,
                callback=self.on_stream_update
            )
            print(f"Listening for stream updates from {self.streamer_name}")
        except Exception as e:
            print(f"Failed to set up EventSub: {e}")

    async def on_stream_update(self, data):
        """Called when the stream information updates."""
        try:
            new_category = data.event.category_name
            if new_category == None or len(new_category) == 0:
                print("Stream category changed to nothing.")
                new_category = "[No Stream Category]"
                await self.update_system_prompt()
                category_empty_message = self.empty_category_template.format(streamer_name=self.streamer_name)
                if category_empty_message and len(category_empty_message) > 0:
                    await self.chat.send_message(self.channel_name, 
                        category_empty_message)
            if new_category != self.current_category:
                old_category = self.current_category
                self.current_category = new_category
                print(f"Stream category changed from {old_category} to {self.current_category}")
                await self.update_system_prompt()
                category_change_message = self.category_change_template.format(old_category=old_category, new_category=self.current_category)
                if category_change_message and len(category_change_message) > 0:
                    await self.chat.send_message(self.channel_name, 
                        category_change_message)
        except Exception as e:
            print(f"Error handling stream update: {e}")

    async def run(self):
        # Connect to Twitch API
        self.twitch = Twitch(self.app_id, self.app_secret)

        # Check if we have a refresh token stored
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                refresh_token = data.get('refresh_token')
                f.close()
            if refresh_token:
                try:
                    token, refresh_token = await refresh_access_token(refresh_token, self.app_id, self.app_secret)
                    with open(self.config_file, 'w') as f:
                        data['refresh_token'] = refresh_token
                        json.dump(data, f)
                        f.close()
                    await self.twitch.set_user_authentication(token, self.user_scope, refresh_token)
                except Exception as e:
                    print(f"Error refreshing token: {e}")
        else:
            # Create authenticator with all required scopes
            try:
                auth = UserAuthenticator(self.twitch, self.user_scope, force_verify=True)
                token, refresh_token = await auth.authenticate()
                # Save token and refresh token to json
                with open(self.config_file, 'w') as f:
                    data = json.load(f)
                    data['refresh_token'] = refresh_token
                    json.dump(data, f)
                await self.twitch.set_user_authentication(token, self.user_scope, refresh_token)
            except Exception as e:
                print(f"Error authenticating with Twitch: {e}")

        # Set up EventSub for game detection
        await self.setup_eventsub()
        
        # Initialize chat
        try:
            self.chat = await Chat(self.twitch)
        except ValueError as e:
            print(f"Error initializing chat: {e}")
            print("It is likely that your Twitch credentials are incorrect. Please check them and try again.")
            return
        
        # Register handlers
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
        
        # Start chat
        self.chat.start()
        
        try:
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
        finally:
            # Clean up
            if self.eventsub:
                await self.eventsub.stop()
            if self.chat:
                self.chat.stop()
            if self.twitch:
                await self.twitch.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Twitch Chat Bot with LLM integration')
    parser.add_argument('--history', type=str, default='./chat_logs/history.json', help='File to save/load chat history (default: ./chat_logs/history.json)')
    parser.add_argument('--configuration', type=str, default='./configuration.json', help='File to load configuration variables from (default: ./configuration.json)')
    parser.add_argument('--model', type=str, default='llama3.2:3b-instruct-q4_0', help='LLM model to use (default: llama3.2:3b-instruct-q4_0)')
    args = parser.parse_args()
    
    history_file = args.history
    if history_file and not history_file.endswith('.json'):
        history_file = f"{history_file}.json"
    
    bot = Bot(history_file=history_file, config_file=args.configuration, model=args.model)

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nShutting down bot...")
        if history_file:
            asyncio.run(bot.save_history())
        print("Goodbye!")
