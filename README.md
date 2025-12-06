# Luma Events Plugin for Red-DiscordBot

A comprehensive Red-DiscordBot plugin for integrating with Luma's public API to fetch and display calendar events across Discord channels. This plugin replaces the previous mock implementation with real Luma API integration.

## Features

### 🔄 Real API Integration
- **Live Data**: Fetches real events from Luma calendar subscriptions
- **No Authentication Required**: Uses Luma's public API endpoints
- **Automatic Updates**: Background task updates events periodically
- **Manual Triggers**: Force updates when needed

### 📊 Smart Caching
- **Intelligent Caching**: 5-minute TTL to reduce API calls
- **Auto-cleanup**: Expired cache entries removed automatically
- **Performance Optimized**: Minimizes API usage while maintaining fresh data

### 🛡️ Robust Error Handling
- **Rate Limit Management**: Automatic handling of API rate limits
- **Retry Logic**: Exponential backoff for failed requests
- **Graceful Degradation**: Continues working even with API issues
- **Comprehensive Logging**: Detailed error tracking and debugging

### 🎯 Channel Organization
- **Subscription Management**: Add multiple Luma calendar subscriptions
- **Channel Groups**: Organize events by Discord channels
- **Flexible Display**: Configure max events per channel
- **Permission Control**: Admin-only configuration commands

## Installation

### Method 1: Using Red's Downloader (Recommended)

1. **Add this repository to your Red bot**:
   ```
   [p]repo add luma-redbot https://github.com/yourusername/luma-redbot
   ```

2. **Install the cog**:
   ```
   [p]cog install luma-redbot luma
   ```

3. **Load the cog**:
   ```
   [p]load luma
   ```

### Method 2: Manual Installation

1. **Clone or copy the plugin files** to your Red-DiscordBot's `cogs/` directory:
   ```
   your-redbot-instance/
   └── cogs/
       └── luma/
           ├── __init__.py
           ├── luma.py
           ├── api_client.py
           ├── data_models.py
           ├── info.json
           └── README.md
   ```

2. **Install required dependencies** (if not already installed):
   ```bash
   pip install aiohttp pydantic
   ```

3. **Load the plugin** in your bot:
   ```bash
   [p]load luma
   ```

## Configuration

### Basic Setup

1. **Add a Luma Calendar Subscription**:
   ```bash
   [p]luma subscriptions add <api_id> <slug> <name>
   ```
   - `api_id`: The API ID of the Luma calendar
   - `slug`: The calendar's URL slug (e.g., "my-calendar")
   - `name`: A friendly name for identification

2. **Create a Channel Group**:
   ```bash
   [p]luma groups create <group_name> #channel-name <max_events>
   ```

3. **Add Subscription to Group**:
   ```bash
   [p]luma groups addsub <group_name> <subscription_api_id>
   ```

### Configuration Commands

#### Subscription Management
- `[p]luma subscriptions` - List all subscriptions
- `[p]luma subscriptions add <api_id> <slug> <name>` - Add new subscription
- `[p]luma subscriptions remove <api_id>` - Remove subscription

#### Channel Group Management
- `[p]luma groups` - List all channel groups
- `[p]luma groups create <name> <channel> [max_events]` - Create group
- `[p]luma groups addsub <group_name> <api_id>` - Add subscription to group
- `[p]luma groups removesub <group_name> <api_id>` - Remove from group

#### Plugin Configuration
- `[p]luma config` - View current configuration
- `[p]luma config interval <hours>` - Set update interval (1-168 hours)
- `[p]luma config enable` - Enable automatic updates
- `[p]luma config disable` - Disable automatic updates

#### Testing and Maintenance
- `[p]luma update` - Manually trigger event update
- `[p]luma test <api_id>` - Test a specific subscription
- `[p]luma cache` - View cache statistics

## How It Works

### API Integration

The plugin uses Luma's public API endpoints to fetch calendar data:

- **Endpoint**: `https://api.lu.ma/v1/public/calendars/{slug}`
- **Authentication**: None required (public API)
- **Rate Limiting**: 1-second delay between requests
- **Caching**: 5-minute TTL for API responses

### Event Fetching Process

1. **Background Updates**: Automatic updates every 24 hours (configurable)
2. **Subscription Processing**: Fetches events for each configured subscription
3. **Event Filtering**: Shows events from yesterday onwards
4. **Channel Distribution**: Sends formatted events to configured channels
5. **Error Recovery**: Continues processing even if individual subscriptions fail

### Event Display Format

Events are displayed in Discord embeds with:
- **Event Name**: Bold header
- **Date/Time**: Formatted as "YYYY-MM-DD HH:MM UTC"
- **Event Link**: Direct link to the event on Luma
- **Channel Grouping**: Organized by configured channel groups

## API Client Features

### `LumaAPIClient` Class

The `api_client.py` module provides a comprehensive client with:

- **Session Management**: Automatic HTTP session handling
- **Rate Limiting**: Respects API rate limits with adaptive delays
- **Retry Logic**: Exponential backoff for failed requests
- **Caching System**: In-memory caching with TTL
- **Error Handling**: Specific exceptions for different error types
- **Logging**: Detailed operation logging

### Error Types

- `LumaAPIError`: Base exception for all API errors
- `LumaAPIRateLimitError`: Rate limit exceeded
- `LumaAPINotFoundError`: Resource not found
- `LumaAPIAuthError`: Authentication issues
- `LumaAPITimeoutError`: Request timeout

### Cache Management

- **TTL**: 5 minutes by default
- **Automatic Cleanup**: Removes expired entries
- **Cache Statistics**: Available via commands
- **Manual Clear**: Cache can be cleared programmatically

## Troubleshooting

### Common Issues

1. **"Calendar not found"**:
   - Verify the calendar slug is correct
   - Ensure the calendar is public
   - Check for typos in the slug

2. **"No events found"**:
   - The calendar might have no upcoming events
   - Events might be private or require registration
   - Try testing with `[p]luma test <api_id>`

3. **Rate limiting**:
   - The plugin automatically handles rate limits
   - If issues persist, increase update interval
   - Check logs for rate limit warnings

4. **Bot permissions**:
   - Ensure bot has Send Messages permission in target channels
   - Verify channel exists and bot can access it

### Debug Commands

- `[p]luma test <api_id>`: Test individual subscription
- `[p]luma cache`: View cache statistics
- Check bot logs for detailed error information

### Logging

The plugin provides detailed logging at the `red.luma` logger level:
- **INFO**: Successful operations
- **WARNING**: Rate limits and recoverable errors
- **ERROR**: API failures and configuration issues

Enable debug logging with:
```bash
[p]set logger red.luma level debug
```

## Configuration Example

Complete setup example:

```bash
# 1. Add a subscription
[p]luma subscriptions add abc123 my-company-events "Company Events"

# 2. Create a channel group
[p]luma groups create announcements #announcements 10

# 3. Add subscription to group
[p]luma groups addsub announcements abc123

# 4. Configure update interval
[p]luma config interval 12

# 5. Enable automatic updates
[p]luma config enable

# 6. Test the setup
[p]luma test abc123

# 7. Manual update
[p]luma update
```

## Technical Details

### Dependencies

- **aiohttp**: Async HTTP client
- **pydantic**: Data validation and parsing
- **discord.py**: Discord API wrapper (Redbot dependency)
- **asyncio**: Async/await support

### Data Models

- **Subscription**: Stores Luma calendar subscription info
- **ChannelGroup**: Manages Discord channel event display
- **Event**: Pydantic model for Luma event data
- **LumaConfig**: Plugin configuration structure

### API Endpoints Used

- `GET /v1/public/calendars/{slug}`: Fetch calendar information and events
- Uses Luma's public API (no authentication required)
- Supports pagination and filtering

## Support

For issues, questions, or contributions:
1. Check the troubleshooting section above
2. Review bot logs for detailed error information
3. Test individual components using the test commands
4. Ensure all dependencies are properly installed

## License

This plugin follows the same license as Red-DiscordBot.

---

**Note**: This plugin requires Luma calendar slugs to be public and accessible via the Luma public API. Private calendars or those requiring authentication are not supported.