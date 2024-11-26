import asyncio
from twitchAPI.twitch import Twitch
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand, ChatEvent
from twitchAPI.helper import first
from twitchAPI.type import AuthScope
from twitchAPI.oauth import UserAuthenticator
from ollama import AsyncClient

class Bot:
    def __init__(self):
        self.app_id = input("Enter your Twitch application ID: ")
        self.app_secret = input("Enter your Twitch application secret: ")
        self.channel_name = input("Enter your channel name here: ")
        
        self.streamer_name = input("Enter your streamer's name here (leave blank for channel name): ")
        if not self.streamer_name:
            self.streamer_name = self.channel_name

        self.llm = AsyncClient()
        self.chat_history = []
        self.prompt = f"""
        You are SLM Bot, a chatbot on a Twitch stream alongside your host.
        You are a helpful assistant that chats with the stream chat, answers questions about the streamer's game, etc.
        You should respond to recent messages in the chat history with your response content only. Do not respond with a timestamp, this is added automatically by Twitch!
        The streamer's name is {self.streamer_name}.
        """
        
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
            AuthScope.CHANNEL_READ_VIPS
        ]

        self.twitch = None
        self.chat = None

    async def on_ready(self, ready_event: EventData):
        """Called when the chat connection is ready."""
        try:
            await self.chat.join_room(self.channel_name)
            print(f'Connected to {self.channel_name}\'s chat')
        except Exception as e:
            print(f'Failed to connect to {self.channel_name}\'s chat: {e}')

    async def on_message(self, msg: ChatMessage):
        """Called when a message is received in chat."""
        # Debugging
        print(f"Message from {msg.user.name}: {msg.text}")

        if msg.text.startswith('?'):
            return

        # Add message to chat history
        self.chat_history.append({
            'role': 'user', 
            'content': f"{msg.sent_timestamp} {msg.user.name}: {msg.text}"
        })

        # Get response from LLM
        response = await self.llm.chat(
            model='llama3.2:3b', 
            messages=[{'role': 'system', 'content': self.prompt}] + self.chat_history
        )
        response_text = response['message']['content']

        # Send response to chat
        await self.chat.send_message(self.channel_name, response_text)

    async def on_sub(self, sub: ChatSub):
        """Called when someone subscribes to the channel."""
        print(f"{sub.user.name} just subscribed!")

    async def test_command(self, cmd: ChatCommand):
        """Test command handler."""
        if len(cmd.parameter) == 0:
            await cmd.reply('You did not give me a parameter!')
        else:
            await cmd.reply(f'{cmd.user.name} said: {cmd.parameter}')
    
    async def run(self):
        # Initialize the Twitch instance
        self.twitch = await Twitch(self.app_id, self.app_secret)
        
        print("\nIMPORTANT: When the browser opens:")
        print("1. Make sure you're logged in as your bot account")
        print("2. If you're logged in as another account, log out first")
        print("3. The bot will use whatever account authorizes the application\n")
        
        input("Press Enter when you're ready to proceed with authentication...")
        
        # Create authenticator with all required scopes
        auth = UserAuthenticator(
            self.twitch, 
            self.user_scope,
            force_verify=True  # This forces a login prompt even if already authenticated
        )
        
        # Open authentication webpage in default browser and wait for token
        token, refresh_token = await auth.authenticate()
        
        # Set the acquired tokens on the Twitch instance
        await self.twitch.set_user_authentication(token, self.user_scope, refresh_token)
        
        # Initialize chat
        self.chat = await Chat(self.twitch)
        
        # Register callbacks
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
        self.chat.register_event(ChatEvent.SUB, self.on_sub)
        self.chat.register_event('echo', self.test_command)
        
        # Connect to chat
        self.chat.start()

        # Run until interrupted
        try:
            while self.chat.is_ready:
                await asyncio.sleep(1)  # Use asyncio.sleep instead of input for proper async handling
        except KeyboardInterrupt:
            print("\nShutting down bot...")
        finally:
            if self.chat:
                self.chat.stop()
            if self.twitch:
                await self.twitch.close()


if __name__ == "__main__":
    bot = Bot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        asyncio.get_event_loop().stop()
        print("\nShutting down bot...")
