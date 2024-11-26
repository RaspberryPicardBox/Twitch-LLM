# Twitch LLM Chat Bot

An AI-powered Twitch chat bot that uses local LLM (Language Learning Model) to interact with chat in a natural and engaging way.

## Features

- Natural language responses to chat messages using local LLM
- Subscription event handling
- Command support
- Full Twitch integration with various channel read permissions

## Prerequisites

- Python 3.12+
- A Twitch account for the bot
- A Twitch Developer Application
- Ollama installed locally (for LLM support)

## Setup

### 1. Twitch Developer Console Setup

1. Go to the [Twitch Developer Console](https://dev.twitch.tv/console)
2. Log in with your Twitch account
3. Click "Register Your Application"
4. Fill in the following details:
   - Name: Your bot's name
   - OAuth Redirect URLs: Add `http://localhost:17563` and `http://localhost:3000`
   - Category: Chat Bot
5. Click "Create"
6. You'll receive a Client ID and Client Secret. Keep these safe!

### 2. Bot Account Setup

1. Create a new Twitch account for your bot if you haven't already
2. Note down the account's username

### 3. Environment Setup

1. Clone this repository
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
ollama pull llama3.2:3b
```

## Running the Bot

1. Make sure you're logged out of your personal Twitch account in your browser
2. Start the bot:
```bash
python main.py
```
3. When prompted:
   - Enter your Twitch application client ID
   - Enter your Twitch application secret
   - Enter the channel name where the bot should operate
   - Enter the streamer's name (or leave blank to use channel name)
4. When the browser opens:
   - Log in with your bot's Twitch account
   - Authorize the application with the requested permissions

The bot will connect to the specified channel and start responding to chat messages.

## Permissions

The bot requires the following Twitch permissions:
- Chat Read/Edit
- Bits Read
- Channel Bot
- Channel Read:
  - Charity
  - Goals
  - Hype Train
  - Polls
  - Predictions
  - Redemptions
  - Subscriptions
  - VIPs

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

## Stopping the Bot

Press Ctrl+C in the terminal to gracefully shut down the bot.

## Troubleshooting

### Authentication Issues
- Make sure you're logged out of your personal Twitch account before running the bot
- Use an incognito window if you're having trouble with cached credentials
- Verify that your redirect URLs are correctly set in the Twitch Developer Console

### Connection Issues
- Verify that your Client ID and Secret are correct
- Check that your bot account has not been banned from the channel
- Ensure you have a stable internet connection

### LLM Issues
- Make sure Ollama is running (`ollama serve`)
- Verify that the llama3.2:3b model is properly installed
- Check Ollama logs for any errors

## Contributing

Feel free to submit issues and pull requests!

## License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.

This means you are free to:
- Share and redistribute the material
- Adapt and build upon the material

Under these conditions:
- **Attribution** - You must give credit to RaspberryPicardBox, provide a link to the license, and indicate if changes were made
- **NonCommercial** - You may not use this for commercial purposes
- **ShareAlike** - If you modify this code, you must distribute your contributions under the same license

For more details, see the [LICENSE](LICENSE) file or visit [Creative Commons BY-NC-SA 4.0](http://creativecommons.org/licenses/by-nc-sa/4.0/).
