    async def clear_events_database(self, ctx: commands.Context, group_name: Optional[str] = None):
        """Clear the event tracking database to enable resending notifications.

        This command clears only the event tracking database that prevents
        duplicate notifications. It preserves all your configuration including:
        • All calendar subscriptions
        • All channel groups
        • All configuration settings

        After clearing, all events will be treated as new and can be resent.
        This is useful for testing or when you want to resend notifications
        for events that were previously sent.

        Parameters:
        - group_name: Optional name of a channel group to clear events for only that group.
                     If not specified, clears all events globally.

        Examples:
        `[p]luma database clear` - Clear all event tracking data
        `[p]luma database clear "Weekly Events"` - Clear events for a specific group only
        `[p]luma database clear "Group Name"` - Clear events for the named group
        """
        # Get channel groups for validation
        channel_groups = await self.config.guild(ctx.guild).channel_groups()
        subscriptions = await self.config.guild(ctx.guild).subscriptions()

        # If group_name is specified, validate it exists and has subscriptions
        if group_name:
            if group_name not in channel_groups:
                await ctx.send(
                    f"❌ Channel group `{group_name}` not found. "
                    f"Available groups: {', '.join(channel_groups.keys()) or 'None'}"
                )
                return

            group = ChannelGroup.from_dict(channel_groups[group_name])
            if not group.subscription_ids:
                await ctx.send(
                    f"⚠️ Channel group `{group_name}` has no subscriptions. "
                    "Nothing to clear."
                )
                return

            # Show which calendars will be affected
            affected_calendars = []
            for sub_id in group.subscription_ids:
                if sub_id in subscriptions:
                    sub = Subscription.from_dict(subscriptions[sub_id])
                    affected_calendars.append(f"{sub.name} ({sub.api_id[:12]}...)")
            
            if not affected_calendars:
                await ctx.send(
                    f"⚠️ No valid subscriptions found for group `{group_name}`."
                )
                return

            description = f"This will clear event tracking data for **group: {group_name}** including:\n"
            for calendar in affected_calendars:
                description += f"• {calendar}\n"
            description += f"\n**PRESERVED:**\n• All other groups and their events\n• All configuration settings\n\n**After clearing, events from this group will be treated as new.**"
            
        else:
            # Global clear - get current database stats for confirmation
            try:
                stats = await self.event_db.get_calendar_stats()
                total_events = stats.get("total_events", 0)
                total_sends = stats.get("total_sends", 0)
            except Exception:
                total_events = 0
                total_sends = 0

            description = "This will clear the event tracking database including:\n"
            description += f"• {total_events} tracked events\n"
            description += f"• {total_sends} send history records\n\n"
            description += "**PRESERVED:**\n• All calendar subscriptions\n• All channel groups\n• All configuration settings\n\n**After clearing, all events will be treated as new.**"

        embed = discord.Embed(
            title="⚠️ Clear Event Database",
            description=description,
            color=discord.Color.orange(),
        )
        clear_type = f"**for group: {group_name}**" if group_name else "**GLOBAL CLEAR**"
        embed.add_field(
            name="Scope",
            value=clear_type,
            inline=False,
        )
        embed.add_field(
            name="Confirmation Required",
            value="React with ✅ to confirm or ❌ to cancel.",
            inline=False,
        )

        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        def check(reaction, user):
            return (
                user == ctx.author
                and reaction.message.id == message.id
                and reaction.emoji in ["✅", "❌"]
            )

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=60.0, check=check
            )

            if reaction.emoji == "✅":
                try:
                    # Clear the event database
                    if group_name:
                        # Group-specific clear
                        log.info(f"Starting group-specific clear for group '{group_name}' in guild {ctx.guild.id}")
                        
                        # Get calendar IDs for this group
                        calendar_ids = await self.event_db.get_calendars_for_group(
                            group_name, channel_groups
                        )
                        
                        if not calendar_ids:
                            embed.title = "❌ No Calendars Found"
                            embed.description = f"No calendars found for group `{group_name}`."
                            embed.color = discord.Color.red()
                            await message.edit(embed=embed)
                            return
                        
                        result = await self.event_db.clear_event_database(calendar_ids)
                    else:
                        # Global clear
                        log.info(f"Starting global database clear for guild {ctx.guild.id}")
                        result = await self.event_db.clear_event_database()

                    if result["success"]:
                        if group_name:
                            embed.title = "✅ Group Database Cleared"
                            embed.description = (
                                f"Successfully cleared event tracking data for **group: {group_name}**:\n"
                                f"• {result['events_cleared']} events cleared\n"
                                f"• {result['history_cleared']} history records cleared\n\n"
                                f"Events from this group will now be treated as new."
                            )
                        else:
                            embed.title = "✅ Global Database Cleared"
                            embed.description = (
                                f"Successfully cleared event tracking database:\n"
                                f"• {result['events_cleared']} events cleared\n"
                                f"• {result['history_cleared']} history records cleared\n\n"
                                f"All events will now be treated as new and can be resent."
                            )
                        embed.color = discord.Color.green()

                        log.info(
                            f"User {ctx.author.id} cleared {'group-specific' if group_name else 'global'} "
                            f"event database for guild {ctx.guild.id}: {result['events_cleared']} events, "
                            f"{result['history_cleared']} history records"
                        )
                    else:
                        embed.title = "❌ Failed to Clear Database"
                        embed.description = f"Failed to clear event database: {result.get('error', 'Unknown error')}"
                        embed.color = discord.Color.red()

                except Exception as e:
                    log.error(f"Failed to clear event database: {e}")
                    embed.title = "❌ Error"
                    embed.description = (
                        f"An error occurred while clearing the database: {str(e)}"
                    )
                    embed.color = discord.Color.red()

                await message.edit(embed=embed)

            else:
                embed.title = "❌ Clear Cancelled"
                embed.description = (
                    "Event database clear was cancelled. No changes were made."
                )
                embed.color = discord.Color.blue()
                await message.edit(embed=embed)

        except asyncio.TimeoutError:
            embed.title = "⏰ Clear Cancelled"
            embed.description = "Confirmation timed out. No changes were made."
            embed.color = discord.Color.orange()
            await message.edit(embed=embed)