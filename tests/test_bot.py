import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import json
import os
from datetime import datetime

# Import the Bot class
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import Bot

class MockChatMessage:
    """Mock ChatMessage for testing"""
    def __init__(self, user_name, text):
        self.user = MagicMock()
        self.user.name = user_name
        self.text = text
        self.sent_timestamp = datetime.now().isoformat()

class MockEventData:
    """Mock EventData for testing"""
    def __init__(self, category_name="Test Game"):
        self.category_name = category_name

class TestTwitchBot(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up test cases"""
        # Create a temporary directory for test files
        self.test_dir = "test_files"
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create test files
        self.history_file = os.path.join(self.test_dir, "test_history.json")
        self.login_file = os.path.join(self.test_dir, "test_login.json")
        self.prompt_file = os.path.join(self.test_dir, "test_prompt.txt")
        
        # Create test login file
        login_data = {
            "app_id": "test_id",
            "app_secret": "test_secret",
            "channel_name": "test_channel",
            "streamer_name": "test_streamer"
        }
        with open(self.login_file, 'w') as f:
            json.dump(login_data, f)
        
        # Create test prompt file
        with open(self.prompt_file, 'w') as f:
            f.write("Test prompt for {streamer_name} playing {game_playing}")
        
        # Initialize bot with test files
        self.bot = Bot(
            history_file=self.history_file,
            login_file=self.login_file,
            prompt_file=self.prompt_file
        )
        
        # Mock Twitch and Chat
        self.bot.twitch = AsyncMock()
        self.bot.chat = AsyncMock()
        self.bot.llm = AsyncMock()

    async def asyncTearDown(self):
        """Clean up after tests"""
        # Remove test files
        for file in [self.history_file, self.login_file, self.prompt_file]:
            if os.path.exists(file):
                os.remove(file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    async def test_game_change(self):
        """Test game change detection and prompt update"""
        # Setup
        old_game = "Old Game"
        new_game = "New Game"
        self.bot.game_playing = old_game
        
        # Create mock event data
        event_data = MockEventData(category_name=new_game)
        
        # Test game change
        await self.bot.on_stream_update(event_data)
        
        # Assertions
        self.assertEqual(self.bot.game_playing, new_game)
        self.bot.chat.send_message.assert_called_once()
        message = self.bot.chat.send_message.call_args[0][1]
        self.assertIn(old_game, message)
        self.assertIn(new_game, message)

    async def test_chat_message_handling(self):
        """Test chat message handling"""
        # Setup
        self.bot.llm.chat = AsyncMock(return_value={"message": {"content": "Test response"}})
        self.bot.chat_history = []  # Clear history before test
        
        # Create test message
        test_message = MockChatMessage("test_user", "Hello bot!")
        
        # Test message handling
        await self.bot.on_message(test_message)
        
        # Assertions
        self.assertEqual(len(self.bot.chat_history), 2)  # User message + bot response
        self.assertEqual(self.bot.chat_history[0]['role'], 'user')
        self.assertEqual(self.bot.chat_history[1]['role'], 'assistant')
        self.assertIn('test_user', self.bot.chat_history[0]['content'])
        self.assertIn('Hello bot!', self.bot.chat_history[0]['content'])
        self.bot.llm.chat.assert_called_once()
        self.bot.chat.send_message.assert_called_once()

    async def test_command_handling(self):
        """Test command handling"""
        # Setup
        command = MagicMock()
        command.parameter = "test parameter"
        command.user.name = "test_user"
        command.reply = AsyncMock()
        
        # Test command
        await self.bot.test_command(command)
        
        # Assertions
        command.reply.assert_called_once_with("test_user said: test parameter")

    async def test_chat_history_persistence(self):
        """Test chat history saving and loading"""
        # Setup - write test history file directly
        test_history = [{
            "role": "user",
            "content": "Test message",
            "timestamp": datetime.now().isoformat(),
            "username": "test_user"
        }]
        
        with open(self.history_file, 'w') as f:
            json.dump(test_history, f)
        
        # Initialize bot with test history file
        self.bot = Bot(
            history_file=self.history_file,
            login_file=self.login_file,
            prompt_file=self.prompt_file
        )
        
        # Assertions
        self.assertEqual(len(self.bot.chat_history), 1)
        self.assertEqual(self.bot.chat_history[0]["content"], test_history[0]["content"])

    async def test_prompt_template(self):
        """Test prompt template formatting"""
        # Setup
        self.bot.streamer_name = "TestStreamer"
        self.bot.game_playing = "TestGame"
        
        # Test prompt update
        await self.bot.update_system_prompt()
        
        # Assertions
        self.assertIn("TestStreamer", self.bot.prompt)
        self.assertIn("TestGame", self.bot.prompt)

if __name__ == '__main__':
    unittest.main()
