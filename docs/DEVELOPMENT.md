# Development Guide

This guide covers development practices, testing, and contribution guidelines for the Twitch LLM Chat Bot.

## Project Structure

```
.
├── main.py              # Main bot implementation
├── docs/               
│   ├── VARIABLES.md     # Template variable documentation
│   └── DEVELOPMENT.md   # This development guide
├── tests/
│   ├── test_bot.py      # Bot test suite
│   └── requirements-test.txt  # Test dependencies
├── prompt_template.txt  # Default bot personality template
└── README.md           # Project overview
```

## Development Environment

1. Python Version
   - Python 3.12+ required
   - Use a virtual environment:
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # Linux/Mac
     # or
     .venv\Scripts\activate     # Windows
     ```

2. Dependencies
   - Install main dependencies:
     ```bash
     pip install -r requirements.txt
     ```
   - Install test dependencies:
     ```bash
     pip install -r tests/requirements-test.txt
     ```

## Testing

### Test Structure

The test suite uses Python's `unittest` framework with `pytest` for running tests. Tests are located in `tests/test_bot.py`.

1. Test Categories:
   - Game Detection (`test_game_change`)
   - Chat Handling (`test_chat_message_handling`)
   - Command Processing (`test_command_handling`)
   - History Management (`test_chat_history_persistence`)
   - Prompt System (`test_prompt_template`)

2. Mock Objects:
   ```python
   # Mock chat message
   class MockChatMessage:
       def __init__(self, user_name, text):
           self.user = MagicMock()
           self.user.name = user_name
           self.text = text
           self.sent_timestamp = datetime.now().isoformat()

   # Mock stream update
   class MockEventData:
       def __init__(self, category_name="Test Game"):
           self.category_name = category_name
   ```

### Running Tests

1. Basic Test Run:
   ```bash
   python -m pytest tests/test_bot.py -v
   ```

2. With Coverage Report:
   ```bash
   python -m pytest tests/test_bot.py --cov=main -v
   ```

3. Single Test Category:
   ```bash
   python -m pytest tests/test_bot.py -v -k "test_chat_message"
   ```

### Adding New Tests

When adding features to the bot, follow this testing workflow:

1. Create Test First:
   ```python
   async def test_new_feature(self):
       """Test description"""
       # Setup
       self.bot.some_dependency = AsyncMock()
       
       # Execute
       result = await self.bot.new_feature()
       
       # Assert
       self.assertEqual(result, expected_value)
   ```

2. Run Tests to Verify Failure
3. Implement Feature
4. Run Tests to Verify Success

### Mocking Guidelines

1. External Services:
   ```python
   # Mock Twitch API
   self.bot.twitch = AsyncMock()
   
   # Mock LLM
   self.bot.llm.chat = AsyncMock(
       return_value={"message": {"content": "Test response"}}
   )
   ```

2. File Operations:
   ```python
   # Test files are created in temporary directory
   self.test_dir = "test_files"
   os.makedirs(self.test_dir, exist_ok=True)
   ```

## Common Development Tasks

### 1. Adding New Commands

1. Add command handler in `main.py`:
   ```python
   async def new_command(self, cmd: ChatCommand):
       """Handle new command"""
       await cmd.reply(f"New command response")
   ```

2. Add test in `test_bot.py`:
   ```python
   async def test_new_command(self):
       """Test new command"""
       command = MagicMock()
       command.reply = AsyncMock()
       await self.bot.new_command(command)
       command.reply.assert_called_once()
   ```

### 2. Adding Game Detection Features

1. Extend `on_stream_update` in `main.py`
2. Add test case:
   ```python
   async def test_game_feature(self):
       """Test game-specific feature"""
       event_data = MockEventData(category_name="Specific Game")
       await self.bot.on_stream_update(event_data)
       # Add assertions
   ```

### 3. Modifying Chat Behavior

1. Update `on_message` in `main.py`
2. Update test assertions:
   ```python
   async def test_chat_behavior(self):
       """Test modified chat behavior"""
       # Setup message
       test_message = MockChatMessage("user", "test")
       
       # Test behavior
       await self.bot.on_message(test_message)
       
       # Verify new behavior
       self.assertIn("expected_content", 
                    self.bot.chat_history[-1]["content"])
   ```

## Best Practices

1. Code Style
   - Follow PEP 8
   - Use type hints
   - Document all functions and classes

2. Testing
   - Write tests for new features
   - Update tests when modifying existing features
   - Keep tests isolated and independent
   - Use meaningful test names and descriptions

3. Git Workflow
   - Create feature branches
   - Write descriptive commit messages
   - Update tests before merging

4. Documentation
   - Update relevant documentation when adding features
   - Include examples in docstrings
   - Keep README.md up to date

## Troubleshooting Tests

Common issues and solutions:

1. Credential Prompts in Tests
   - Use `login_file` in test setup
   - Mock credential input if needed

2. Async Test Failures
   - Ensure proper async/await usage
   - Check for unhandled coroutines

3. Mock Response Format
   - Match exact API response structure
   - Check mock return values

4. History File Conflicts
   - Use temporary test directories
   - Clean up files after tests
