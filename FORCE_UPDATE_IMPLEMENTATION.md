# Force Update Implementation

## Overview

The force update feature has been successfully implemented in the Luma cog to bypass new event detection and send all events to Discord channels regardless of their new status.

## Implementation Details

### New Command Structure

The existing `[p]luma update` command has been enhanced with an optional `force` parameter:

- **`[p]luma update`** - Normal mode: Only sends new events (existing behavior)
- **`[p]luma update force`** - Force mode: Sends ALL recent events regardless of new status

### Key Changes Made

#### 1. Command Signature Update

```python
# Before
async def manual_update(self, ctx: commands.Context):

# After  
async def manual_update(self, ctx: commands.Context, force: bool = False):
```

#### 2. Force Mode Logic

The implementation modifies the `check_for_changes` logic based on the force parameter:

```python
# Determine check_for_changes based on force parameter
check_for_changes = not force

# In force mode, we bypass change detection and send all events
if force:
    # Send all events regardless of new status
    check_for_changes = False
else:
    # Normal behavior: only send new events
    check_for_changes = True
```

#### 3. Event Sending Logic

**Normal Mode (`[p]luma update`):**
- Uses `check_for_changes=True` to detect new events
- Only sends events if `new_events_count > 0`
- Message: "Found and sent X new event(s) to channels!"

**Force Mode (`[p]luma update force`):**
- Uses `check_for_changes=False` to get all recent events
- Sends ALL events found, regardless of new status
- Message: "Force mode: Sent X event(s) to channels!"

#### 4. User Feedback

Enhanced embed messages provide clear feedback about which mode is active:

- **Normal Mode**: "🔄 Checking for new events..."
- **Force Mode**: "🔄 Force mode: Sending ALL recent events to channels..."

## Technical Implementation

### How Force Mode Works

1. **Bypasses New Event Detection**: Sets `check_for_changes=False`
2. **Fetches All Recent Events**: Gets all events from the last 24 hours
3. **Ignores New Status**: Sends events regardless of whether they're "new" or "seen"
4. **Maintains Message Formatting**: Uses the same rich embed format

### Database Integration

- **Normal Mode**: Uses database change tracking via `event_db.upsert_events()` and `event_db.get_new_events()`
- **Force Mode**: Fetches fresh events from API but doesn't track changes in database

### Error Handling

- Both modes maintain all existing error handling
- Failed events don't prevent other events from being sent
- Clear error messages for API failures

## Usage Examples

### Testing the Message Sending System

```bash
[p]luma update force
```

This command will:
- Fetch all recent events from all subscriptions
- Send them to all configured channel groups
- Ignore whether events are "new" or have been seen before
- Provide clear feedback about the force mode operation

### Re-sending Messages for Existing Events

```bash
[p]luma update force
```

Useful when:
- Testing message formatting
- Re-populating channels with events
- Verifying the message sending system works correctly

### Normal New Events Check

```bash
[p]luma update
```

This maintains the existing behavior:
- Only sends truly new events
- Updates the database with event changes
- Provides standard update feedback

## Benefits

1. **Testing**: Perfect for testing the message sending system without waiting for new events
2. **Repopulation**: Can re-send all recent events to channels for testing or re-population
3. **Debugging**: Useful for debugging event detection and message formatting
4. **Flexibility**: Maintains backward compatibility while adding powerful new functionality

## Backward Compatibility

- Existing `[p]luma update` command behavior is unchanged
- All existing functionality is preserved
- Force mode is an optional enhancement
- Database change tracking continues to work normally

## Code Changes Summary

**File Modified**: `luma/core/luma.py`

**Lines Changed**: 
- Line 1597: Updated method signature to accept `force` parameter
- Lines 1598-1605: Updated docstring to document the force parameter
- Lines 1614-1623: Added force mode detection and user feedback
- Lines 1636-1658: Enhanced event sending logic for both modes
- Lines 1660-1673: Updated success/failure message formatting

The implementation is minimal, focused, and maintains the existing code architecture while adding the requested force functionality.