# Twitch LLM Chat Bot

An AI-powered Twitch chat bot that uses local LLM (Language Learning Model) to interact with chat in a natural and engaging way.

## Features

- Natural language responses to chat messages using local LLM using the `!ai` command
- Event handling support, including custom messages for follows, subs, etc
- Chat history persistence with optional save/load functionality

## Prerequisites

- Python 3.12+
- A Twitch account for the bot (or your own Twitch account)
- Twitch API credentials
- Ollama installed locally (Further support for cloud-based LLMs such as OpenAI's GPT is planned)

## Setup

### 1. Twitch Developer Console Setup

1. Go to the [Twitch Developer Console](https://dev.twitch.tv/console)
2. Log in with your Twitch account
3. Click "Register Your Application" under the Applications section
4. Fill in the following details:
   - Name: Your bot's name; this is not shown in Twitch but is simply a placeholder here
   - OAuth Redirect URLs: Add `http://localhost:17563`
   - Category: Chat Bot
5. Click "Create"
6. You'll receive a Client ID and Client Secret. Keep these safe!

<p align="center">
  <b><font color="red">NEVER SHARE YOUR CLIENT ID OR CLIENT SECRET WITH ANYONE. SHARING THESE IDS CAN RESULT IN ANY NUMBER OF PEOPLE HAVING ACCESS TO YOUR BOT ACCOUNT</font></b>
</p>

### 2. Bot Account Setup

1. Create a new Twitch account for your bot if you haven't already
2. Note down the account's username

This is the user that the bot program will be controlling. Alternatively, you can use your own account, however this will show as though *you* are speaking in your chat when the `!ai` command is used.

### 3. Environment Setup

1. Clone this repository using `git clone https://github.com/RaspberryPicardBox/Twitch-LLM.git`
2. Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 4. Ollama Setup

1. Install Ollama following the instructions at [Ollama's website](https://ollama.ai)
2. Pull the required model:
```bash
ollama pull llama3.2:3b-instruct-q4_0
```

## Running the Bot

### Basic Usage
```bash
python main.py
```

### Command Line Arguments
```bash
# Use all features
python main.py --login credentials.json --history chat_logs/history --prompt custom_prompt.txt

# --login - Use saved credentials
# --history - Enable chat history saving
# --prompt - Use custom prompt from a text file
# --model - Use a different LLM model
```

If you are unsure how to use any of the above, use `python main.py --help` to view further information.

When you start the bot:
1. Make sure you're logged out of your personal Twitch account in your browser
2. You'll be prompted for credentials (if not using --login)
3. A browser window will open for OAuth authentication
   - Log in with your bot's Twitch account
   - Authorize the application

### Using Saved Credentials
You can save your Twitch credentials in a JSON file to avoid entering them each time:

```bash
# Use saved credentials
python main.py --login my_login.json
```

Create a JSON file with your credentials (see `login_template.json` for format):
```json
{
    "app_id": "your_twitch_app_id_here",
    "app_secret": "your_twitch_app_secret_here",
    "channel_name": "your_channel_name_here",
    "streamer_name": "streamer_name_here"  // Optional
}
```

⚠️ **Important**: Login files are automatically added to `.gitignore` to prevent accidental commits. Never commit files containing your credentials!

### Using Custom Prompts
You can customize the bot's personality and behavior using a prompt template:

```bash
# Use custom prompt
python main.py --prompt my_prompt.txt
```

The prompt template can include variables that are automatically updated:
- `{streamer_name}` - The name of the streamer
- `{current_category}` - The current category being streamed

See [docs/VARIABLES.md](docs/VARIABLES.md) for detailed information about available variables and their usage.

Example templates are provided:
- `prompt_template.txt` - Default bot personality
- Create your own by copying and modifying the template

### Using Chat History
The bot maintains a rolling history, which can be optionally saved and loaded:

```bash
# Save history to a specific file
python main.py --history chat_logs/stream_20240126

# Load previous history and continue saving
python main.py --history chat_logs/existing_history
```

Chat history features:
- Files are saved in JSON format (`.json` extension added automatically)
- History is saved after each message
- Previous history is loaded on startup if the file exists
- Directory structure is created automatically

## Available Tools

The Twitch Chat Bot includes several tools that it calls upon automatically to enhance interaction and functionality:

1. **respond_to_user**: 
   - **Description**: Skips the tool call and sends a message to the user.
   - **Parameters**: None required.

2. **search_internet**: 
   - **Description**: Searches the internet using DuckDuckGo and returns up to 3 results. This tool is used only when a chat user asks for an internet search.
   - **Parameters**:
     - `query` (string): The query to search for.

3. **get_current_time**: 
   - **Description**: Retrieves the current time in ISO format.
   - **Parameters**: None required.

These tools enable the bot to interact effectively with users and provide relevant information as needed.

## Permissions

The bot requires the following Twitch permissions:
- Chat Read/Edit (to read and respond to chat)
- Channel Subscriptions Read (to detect new subscribers)
- Moderator-level Channel Follower Read (to detect new followers)

These permissions allow the bot to fully interact with chat and access various channel events.

## Security

This application requires several sensitive credentials:
- Twitch Application ID
- Twitch Application Secret
- OAuth tokens (generated during runtime)

These credentials are handled securely:
1. No sensitive information is hardcoded
2. All credentials are requested at runtime
3. OAuth tokens are managed by the TwitchAPI library
4. The `.gitignore` file prevents sensitive files from being committed

⚠️ **Never commit any files containing your Twitch Application ID, Secret, or tokens to version control!**

**Never share your Twitch Application ID, Secret, or tokens with anyone!**

## Stopping the Bot

Press Ctrl+C in the terminal to gracefully shut down the bot. If chat history is enabled, it will be saved before exit.

## Troubleshooting

### Authentication Issues
- Make sure you're logged out of your personal Twitch account before running the bot (unless this is the account you wish to use)
- Use an incognito window if you're having trouble with cached credentials
- Verify that your redirect URLs are correctly set in the Twitch Developer Console

### Connection Issues
- Verify that your Client ID and Secret are correct
- Check that your bot account has not been banned from the channel
- Ensure you have a stable internet connection

### LLM Issues
- Make sure Ollama is running (`ollama serve`)
- Verify that the selected model is properly installed
- Check Ollama logs for any errors

### Chat History Issues
- Ensure you have write permissions in the target directory
- Check that the history file is valid JSON if loading existing history
- Verify that the chat logs directory exists and is writable

## Contributing

Feel free to submit issues and pull requests!

# Todo List

- [ ] Add logging for better error handling
- [ ] Add better exception handling for Ollama errors
- [ ] Add more cool commands and functionality
- [ ] Add support for cloud-based LLMs
- [ ] Add support for variable chat history save lengths

## License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.

Under these conditions:
- **Attribution** - You must give credit to RaspberryPicardBox, provide a link to the license, and indicate if changes were made
- **NonCommercial** - You may not use this for commercial purposes
- **ShareAlike** - If you modify this code, you must distribute your contributions under the same license

For more details, see the [LICENSE](LICENSE) file or visit [Creative Commons BY-NC-SA 4.0](http://creativecommons.org/licenses/by-nc-sa/4.0/).
