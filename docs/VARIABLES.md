# Template Variables Reference

When creating custom system prompts for the bot, you can use these variables to make your prompt dynamic. Variables are replaced with their actual values when the bot starts and when game information updates.

## Available Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `{streamer_name}` | The name of the streamer | "RaspberryPicardBox" |
| `{current_category}` | The current category being streamed | "Just Chatting", "[Stream Offline]", "[Unknown Category]" |

## Variable States

### Game States
The `{current_category}` variable can have several states:
- Active game name (e.g., "Minecraft", "Just Chatting")
- "[Stream Offline]" when the stream is not live
- "[No Stream Category]" when the stream has no category
- "[Unknown Category]" if there's an error detecting the game

## Using Variables in Templates

1. Create a text file with your custom prompt
2. Use variables by surrounding them with curly braces
3. Pass the file to the bot using `--prompt your_prompt.txt`

### Example Template
```txt
You are a helpful bot in {streamer_name}'s chat.
The stream is currently playing {game_playing}.

Please keep your responses friendly and related to the current game when possible.
```

## Tips for Template Creation

1. Always test your template with various game states
2. Consider what happens when the stream is offline
3. Keep the core bot personality consistent
4. Use the example chat format to demonstrate desired behavior
5. Remember that variables are updated automatically when:
   - The bot starts up
   - The streamer changes category
   - The stream goes online/offline
