import asyncio
from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand, ChatEvent
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
    
    def __init__(self, history_file=None, login_file=None, prompt_file=None):
        if login_file and os.path.exists(login_file):
            try:
                with open(login_file, 'r') as f:
                    login_data = json.load(f)
                self.app_id = login_data.get('app_id')
                self.app_secret = login_data.get('app_secret')
                self.channel_name = login_data.get('channel_name')
                self.streamer_name = login_data.get('streamer_name', self.channel_name)
                self.bot_name = login_data.get('bot_name', 'SLM_Bot')
                print("Loaded credentials from login file")
            except Exception as e:
                print(f"Error loading login file: {e}")
                self._prompt_credentials()
        else:
            self._prompt_credentials()

        self.llm = AsyncClient()
        self.chat_history = []
        self.history_file = history_file
        self.prompt_file = prompt_file

        # This is updated automatically! Do not set this manually.
        self.game_playing = ""
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
            AuthScope.BITS_READ,
            AuthScope.CHANNEL_BOT,
            AuthScope.CHANNEL_READ_CHARITY,
            AuthScope.CHANNEL_READ_GOALS,
            AuthScope.CHANNEL_READ_HYPE_TRAIN,
            AuthScope.CHANNEL_READ_POLLS,
            AuthScope.CHANNEL_READ_PREDICTIONS,
            AuthScope.CHANNEL_READ_REDEMPTIONS,
            AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
            AuthScope.CHANNEL_READ_VIPS,
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
        if self.prompt_file and os.path.exists(self.prompt_file):
            try:
                with open(self.prompt_file, 'r') as f:
                    template = f.read()
                self.prompt = template.format(
                    streamer_name=self.streamer_name,
                    game_playing=self.game_playing
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
        The current game is {self.game_playing}. If the stream is offline, feel free to chat still.

        Example Chat:
            viewer123: Hello bot!
            {self.bot_name}: Hi there! Welcome to the stream! What game are you watching today?
            viewer123: {self.streamer_name} is playing {self.game_playing} today.

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
                    self.game_playing = stream.game_name
                    print(f"Detected game: {self.game_playing}")
                else:
                    self.game_playing = "[Stream Offline]"
                    print("Stream appears to be offline")
            except Exception as e:
                self.game_playing = "[Unknown Game]"
                print(f"Could not detect current game: {e}")

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
                model='llama3.2:3b-instruct-q4_0', 
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

    async def on_message(self, msg: ChatMessage):
        """Called when a message is received in chat."""

        if not msg.text.startswith('!ai'):
            return

        msg.text = msg.text[4:].strip()

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

    async def on_sub(self, sub: ChatSub):
        """Called when someone subscribes to the channel."""
        print(f"{sub.user.name} just subscribed!")
        await self.chat.send_message(self.channel_name, f"Thanks for subscribing, {sub.user.name}!")

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
            await self.eventsub.listen_channel_update(
                broadcaster_user_id=self.user_id,
                callback=self.on_stream_update
            )
            print(f"Listening for stream updates from {self.streamer_name}")
        except Exception as e:
            print(f"Failed to set up EventSub: {e}")

    async def on_stream_update(self, data):
        """Called when the stream information updates."""
        try:
            new_game = data.category_name
            if new_game != self.game_playing:
                old_game = self.game_playing or "[No Game]"
                self.game_playing = new_game
                print(f"Game changed from {old_game} to {self.game_playing}")
                await self.update_system_prompt()
                await self.chat.send_message(self.channel_name, 
                    f"I notice we've switched from {old_game} to {self.game_playing}! Let me update my knowledge.")
        except Exception as e:
            print(f"Error handling stream update: {e}")

    async def run(self):
        # Connect to Twitch API
        self.twitch = Twitch(self.app_id, self.app_secret)

        # Check if we have a refresh token stored
        refresh_token_file = 'token.json'
        if os.path.exists(refresh_token_file):
            with open(refresh_token_file, 'r') as f:
                token_data = json.load(f)
                refresh_token = token_data.get('refresh_token')
                if refresh_token:
                    try:
                        token, refresh_token = await refresh_access_token(refresh_token, self.app_id, self.app_secret)
                        with open(refresh_token_file, 'w') as f:
                            json.dump({'refresh_token': refresh_token}, f)
                        await self.twitch.set_user_authentication(token, self.user_scope, refresh_token)
                    except Exception as e:
                        print(f"Error refreshing token: {e}")
                        os.remove(refresh_token_file)
        else:
            # Create authenticator with all required scopes
            try:
                auth = UserAuthenticator(self.twitch, self.user_scope, force_verify=True)
                token, refresh_token = await auth.authenticate()
                # Save token and refresh token to json
                with open('token.json', 'w') as f:
                    json.dump({'refresh_token': refresh_token}, f)
                await self.twitch.set_user_authentication(token, self.user_scope, refresh_token)
            except Exception as e:
                print(f"Error authenticating with Twitch: {e}")

        # Set up EventSub for game detection
        await self.setup_eventsub()
        
        # Initialize chat
        self.chat = await Chat(self.twitch)
        
        # Register handlers
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
        self.chat.register_event(ChatEvent.SUB, self.on_sub)
        
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
    parser.add_argument('--history', type=str, help='File to save/load chat history (default: none)')
    parser.add_argument('--login', type=str, help='JSON file containing login credentials')
    parser.add_argument('--prompt', type=str, help='Text file containing custom system prompt template')
    args = parser.parse_args()
    
    history_file = args.history
    if history_file and not history_file.endswith('.json'):
        history_file = f"{history_file}.json"
    
    bot = Bot(history_file=history_file, login_file=args.login, prompt_file=args.prompt)
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nShutting down bot...")
        if history_file:
            asyncio.run(bot.save_history())
        print("Goodbye!")
