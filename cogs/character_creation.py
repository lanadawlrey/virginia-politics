import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL_ID"))

# Firebase initialization (run once per process)
FIREBASE_CRED_JSON = os.getenv("FIREBASE_CRED_JSON")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
if FIREBASE_CRED_JSON and not firebase_admin._apps:
    import json
    cred_dict = json.loads(FIREBASE_CRED_JSON)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        'projectId': FIREBASE_PROJECT_ID
    })
    db = firestore.client()
else:
    db = None

class Character(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="character", description="Start the character creation process via DM.")
    async def character(self, interaction: discord.Interaction):
        # Only send an ephemeral embed, not plaintext
        start_embed = discord.Embed(
            description="**Character Creation & Whitelist Application**\n\n📬 Check your DMs to begin character creation!",
            color=0x1F3C72
        )
        await interaction.response.send_message(embed=start_embed, ephemeral=True)
        try:
            user = interaction.user
            gender_options = ["Male", "Female", "Non-Binary"]
            party_options = ["Republican", "Democrat", "Independent"]
            # New form fields and questions
            questions = [
                ("full_name", "Full Legal Name", "e.g. 'John M. Adams'", True),
                ("dob", "Date of Birth (MM/DD/YYYY)", "e.g. '04/29/1982'", True),
                ("county", "County", "e.g. 'Fairfax County'", True),
                ("house", "House District", "e.g. 'District 17'", True),
                ("senate", "Senate District", "e.g. 'District 43'", True),
                ("gender", "Gender", None, True),
                ("party", "Political Party", None, True),
                ("bio", "Character Biography", "Tell us about your character’s upbringing, education, and political experience.", True),
                ("role", "What position are you planning to apply for?", "e.g. Press Secretary, Secretary of Education", True),
                ("roblox_id", "Roblox User ID", "e.g 1234567890", True)
            ]
            answers = {}
            def check(m):
                return m.author == user and isinstance(m.channel, discord.DMChannel)
            welcome_embed = discord.Embed(
                description="**Welcome to Virginia Politics**\n\nVirginia Politics is a community that gathers to simulate the intricate world of politics and policy-making within the State of Virginia.\n\nAs apart of these efforts, we incorporate highly individualized and realistic characters tailored to you. Please be thoughtful, concise, and articulate within your character application for it will be used in its entirely here.\n\n**To begin creating your character, follow along with the prompts below. When you are done, please review your character and then submit.**",
                color=0x1F3C72
            )
            await user.send(embed=welcome_embed)
            total_steps = len(questions)
            step_num = 0
            for key, label, placeholder, required in questions:
                step_num += 1
                progress = f"Step {step_num} of {total_steps}"
                if key == "gender":
                    gender_embed = discord.Embed(
                        description=f"**Character Creation & Whitelist Application**\n\n{progress}\n\n**{label}**\nPlease select your gender:",
                        color=0x1F3C72
                    )
                    class GenderView(discord.ui.View):
                        def __init__(self, timeout=180):
                            super().__init__(timeout=timeout)
                            self.value = None
                        @discord.ui.button(label="Male", style=discord.ButtonStyle.primary)
                        async def male(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                            self.value = "Male"
                            await interaction_button.response.defer()
                            self.stop()
                        @discord.ui.button(label="Female", style=discord.ButtonStyle.primary)
                        async def female(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                            self.value = "Female"
                            await interaction_button.response.defer()
                            self.stop()
                        @discord.ui.button(label="Non-Binary", style=discord.ButtonStyle.primary)
                        async def nb(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                            self.value = "Non-Binary"
                            await interaction_button.response.defer()
                            self.stop()
                    gender_view = GenderView()
                    await user.send(embed=gender_embed, view=gender_view)
                    await gender_view.wait()
                    if gender_view.value:
                        answers[key] = gender_view.value
                    else:
                        await user.send(embed=discord.Embed(description=f"**Character Creation & Whitelist Application**\n\nThis field is required.", color=0x1F3C72))
                        return
                elif key == "party":
                    party_embed = discord.Embed(
                        description=f"**Character Creation & Whitelist Application**\n\n{progress}\n\n**{label}**\nPlease select your political party:",
                        color=0x1F3C72
                    )
                    class PartyView(discord.ui.View):
                        def __init__(self, timeout=180):
                            super().__init__(timeout=timeout)
                            self.value = None
                        @discord.ui.button(label="Republican", style=discord.ButtonStyle.primary)
                        async def rep(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                            self.value = "Republican"
                            await interaction_button.response.defer()
                            self.stop()
                        @discord.ui.button(label="Democrat", style=discord.ButtonStyle.primary)
                        async def dem(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                            self.value = "Democrat"
                            await interaction_button.response.defer()
                            self.stop()
                        @discord.ui.button(label="Independent", style=discord.ButtonStyle.primary)
                        async def ind(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                            self.value = "Independent"
                            await interaction_button.response.defer()
                            self.stop()
                    party_view = PartyView()
                    await user.send(embed=party_embed, view=party_view)
                    await party_view.wait()
                    if party_view.value:
                        answers[key] = party_view.value
                    else:
                        await user.send(embed=discord.Embed(description=f"**Character Creation & Whitelist Application**\n\nThis field is required.", color=0x1F3C72))
                        return
                elif key == "dob":
                    dob_embed = discord.Embed(
                        description=f"**Character Creation & Whitelist Application**\n\n{progress}\n\n**{label}**\n{placeholder}",
                        color=0x1F3C72
                    )
                    await user.send(embed=dob_embed)
                    while True:
                        msg = await self.bot.wait_for('message', check=check, timeout=300)
                        dob = msg.content.strip()
                        import re
                        if re.match(r"^(0[1-9]|1[0-2])/(0[1-9]|[12][0-9]|3[01])/\d{4}$", dob):
                            answers[key] = dob
                            break
                        else:
                            await user.send(embed=discord.Embed(description=f"**Character Creation & Whitelist Application**\n\nPlease use MM/DD/YYYY format.", color=0x1F3C72))
                else:
                    prompt = f"**Character Creation & Whitelist Application**\n\n{progress}\n\n**{label}**"
                    if placeholder:
                        prompt += f"\n{placeholder}"
                    embed = discord.Embed(description=prompt, color=0x1F3C72)
                    await user.send(embed=embed)
                    while True:
                        msg = await self.bot.wait_for('message', check=check, timeout=300)
                        value = msg.content.strip()
                        if required and not value:
                            await user.send(embed=discord.Embed(description=f"**Character Creation & Whitelist Application**\n\nThis field is required.", color=0x1F3C72))
                        else:
                            answers[key] = value
                            break
                # Show current progress summary after each step
                summary_embed = discord.Embed(
                    description=f"**Current Progress**\n\n{chr(0x1F4C4)} **{label}:** {answers.get(key, '')}",
                    color=0x1F3C72
                )
                await user.send(embed=summary_embed)
            # Ask for portrait upload with buttons
            class PortraitView(discord.ui.View):
                def __init__(self, timeout=120):
                    super().__init__(timeout=timeout)
                    self.portrait_url = None
                    self.skip = False
                    self.ready_for_upload = False
                @discord.ui.button(label="Upload Portrait", style=discord.ButtonStyle.primary)
                async def upload(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                    self.ready_for_upload = True
                    await interaction_button.response.send_message(embed=discord.Embed(description="**Character Creation & Whitelist Application**\n\nPlease upload your portrait as an attachment in this DM.", color=0x1F3C72), ephemeral=True)
                    self.stop()
                @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary)
                async def skip(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                    self.skip = True
                    await interaction_button.response.send_message(embed=discord.Embed(description="**Character Creation & Whitelist Application**\n\nPortrait upload skipped.", color=0x1F3C72), ephemeral=True)
                    self.stop()
            portrait_embed = discord.Embed(
                description="**Character Creation & Whitelist Application**\n\nWould you like to upload a portrait of your character?",
                color=0x1F3C72
            )
            view = PortraitView()
            await user.send(embed=portrait_embed, view=view)
            await view.wait()
            portrait_url = None
            if not view.skip and view.ready_for_upload:
                def check_attachment(m):
                    return m.author == user and isinstance(m.channel, discord.DMChannel) and m.attachments
                try:
                    msg = await self.bot.wait_for('message', check=check_attachment, timeout=120)
                    portrait_url = msg.attachments[0].url
                except Exception:
                    pass
            # Timeout warning before review
            await user.send(embed=discord.Embed(description="**Character Creation & Whitelist Application**\n\n⏰ You have 3 minutes to review and submit your application.", color=0x1F3C72))
            # Review embed before submission
            review_embed = discord.Embed(
                title="🗳️ Review Your Character Application",
                description="**Character Creation & Whitelist Application**\n\nPlease review your application below. If everything looks good, click the **Submit** button to finalize your submission.",
                color=0x1F3C72
            )
            review_embed.add_field(name="Full Legal Name", value=answers["full_name"], inline=False)
            review_embed.add_field(name="Date of Birth (MM/DD/YYYY)", value=answers["dob"], inline=True)
            review_embed.add_field(name="County", value=answers["county"], inline=True)
            review_embed.add_field(name="House District", value=answers["house"], inline=True)
            review_embed.add_field(name="Senate District", value=answers["senate"], inline=True)
            review_embed.add_field(name="Gender", value=answers["gender"], inline=True)
            review_embed.add_field(name="Political Party", value=answers["party"], inline=True)
            # Truncate biography if too long for Discord embed field
            bio_value = answers["bio"]
            if len(bio_value) > 1024:
                bio_value = bio_value[:1021] + "..."
            review_embed.add_field(name="Character Biography", value=bio_value, inline=False)
            review_embed.add_field(name="Position Applied For", value=answers["role"], inline=True)
            review_embed.add_field(name="Roblox Username or User ID", value=answers["roblox_id"], inline=True)
            review_embed.set_footer(text=f"Submitted by {user.display_name}")
            if portrait_url:
                review_embed.set_image(url=portrait_url)
            # Send review embed with Submit/Cancel buttons
            class ReviewView(discord.ui.View):
                def __init__(self, timeout=180):
                    super().__init__(timeout=timeout)
                    self.submitted = False
                @discord.ui.button(label="Submit", style=discord.ButtonStyle.success)
                async def submit(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                    self.submitted = True
                    await interaction_button.response.send_message(embed=discord.Embed(description="**Character Creation & Whitelist Application**\n\n✅ Your character has been submitted for review!", color=0x1F3C72), ephemeral=True)
                    self.stop()
                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
                async def cancel(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                    await interaction_button.response.send_message(embed=discord.Embed(description="**Character Creation & Whitelist Application**\n\n❌ Submission cancelled.", color=0x1F3C72), ephemeral=True)
                    self.stop()
            review_view = ReviewView()
            await user.send(embed=review_embed, view=review_view)
            await review_view.wait()
            if not review_view.submitted:
                timeout_embed = discord.Embed(
                    description="**Character Creation & Whitelist Application**\n\n❌ Submission timed out or cancelled. Please start again if you wish to submit your character.",
                    color=0x1F3C72
                )
                await user.send(embed=timeout_embed)
                return
            # Edit previous answers before submission (disabled per user request)
            # class EditView(discord.ui.View):
            #     def __init__(self, timeout=180):
            #         super().__init__(timeout=timeout)
            #         self.edit_field = None
            #     @discord.ui.button(label="Edit Answers", style=discord.ButtonStyle.secondary, emoji="✏️")
            #     async def edit(self, interaction_button: discord.Interaction, button: discord.ui.Button):
            #         fields = [q[1] for q in questions]
            #         options = [discord.SelectOption(label=f, value=str(i)) for i, f in enumerate(fields)]
            #         select = discord.ui.Select(placeholder="Select a field to edit...", options=options)
            #         async def select_callback(interaction_select: discord.Interaction):
            #             idx = int(select.values[0])
            #             field_key, field_label, field_placeholder, _ = questions[idx]
            #             await interaction_select.response.send_message(embed=discord.Embed(description=f"**Character Creation & Whitelist Application**\n\nEditing: {field_label}\nPlease enter a new value.", color=0x1F3C72), ephemeral=True)
            #             def check_edit(m):
            #                 return m.author == user and isinstance(m.channel, discord.DMChannel)
            #             msg = await self.bot.wait_for('message', check=check_edit, timeout=180)
            #             answers[field_key] = msg.content.strip()
            #             await interaction_select.followup.send(embed=discord.Embed(description=f"**Character Creation & Whitelist Application**\n\n{field_label} updated!", color=0x1F3C72), ephemeral=True)
            #             self.edit_field = field_key
            #             self.stop()
            #         select.callback = select_callback
            #         view = discord.ui.View()
            #         view.add_item(select)
            #         await interaction_button.response.send_message(embed=discord.Embed(description="**Character Creation & Whitelist Application**\n\nSelect a field to edit:", color=0x1F3C72), view=view, ephemeral=True)
            # edit_view = EditView()
            # await user.send(embed=discord.Embed(description="**Character Creation & Whitelist Application**\n\nWould you like to edit any answers before submitting?", color=0x1F3C72), view=edit_view)
            # await edit_view.wait()
            # After edit, send final review embed
            final_review_embed = discord.Embed(
                title="🗳️ Final Review of Your Character Application",
                description="**Character Creation & Whitelist Application**\n\nPlease review your application one last time. Click **Submit** to finalize your submission, or **Cancel** to abort.",
                color=0x1F3C72
            )
            final_review_embed.add_field(name="Full Legal Name", value=answers["full_name"], inline=False)
            final_review_embed.add_field(name="Date of Birth (MM/DD/YYYY)", value=answers["dob"], inline=True)
            final_review_embed.add_field(name="County", value=answers["county"], inline=True)
            final_review_embed.add_field(name="House District", value=answers["house"], inline=True)
            final_review_embed.add_field(name="Senate District", value=answers["senate"], inline=True)
            final_review_embed.add_field(name="Gender", value=answers["gender"], inline=True)
            final_review_embed.add_field(name="Political Party", value=answers["party"], inline=True)
            # Truncate biography if too long for Discord embed field
            bio_value = answers["bio"]
            if len(bio_value) > 1024:
                bio_value = bio_value[:1021] + "..."
            final_review_embed.add_field(name="Character Biography", value=bio_value, inline=False)
            final_review_embed.add_field(name="Position Applied For", value=answers["role"], inline=True)
            final_review_embed.add_field(name="Roblox Username or User ID", value=answers["roblox_id"], inline=True)
            final_review_embed.set_footer(text=f"Submitted by {user.display_name}")
            if portrait_url:
                final_review_embed.set_image(url=portrait_url)
            await user.send(embed=final_review_embed)
            # Final submit/cancel buttons
            await review_view.wait()
            if not review_view.submitted:
                timeout_embed = discord.Embed(
                    description="**Character Creation & Whitelist Application**\n\n❌ Submission timed out or cancelled. Please start again if you wish to submit your character.",
                    color=0x1F3C72
                )
                await user.send(embed=timeout_embed)
                return
            # After submit, send to mod channel
            # Format Roblox ID as SSN for mods
            roblox_id_raw = answers["roblox_id"].strip()
            roblox_digits = ''.join(filter(str.isdigit, roblox_id_raw))
            roblox_digits = roblox_digits[-9:].rjust(9, '0')
            ssn = f"{roblox_digits[:3]}-{roblox_digits[3:5]}-{roblox_digits[5:]}"
            mod_embed = discord.Embed(
                title="🗳️ New Character Submission",
                description="**Character Creation & Whitelist Application**",
                color=0x1F3C72
            )
            mod_embed.add_field(name="Full Legal Name", value=answers["full_name"], inline=False)
            mod_embed.add_field(name="Date of Birth (MM/DD/YYYY)", value=answers["dob"], inline=True)
            mod_embed.add_field(name="County", value=answers["county"], inline=True)
            mod_embed.add_field(name="House District", value=answers["house"], inline=True)
            mod_embed.add_field(name="Senate District", value=answers["senate"], inline=True)
            mod_embed.add_field(name="Gender", value=answers["gender"], inline=True)
            mod_embed.add_field(name="Political Party", value=answers["party"], inline=True)
            # Truncate biography if too long for Discord embed field
            bio_value = answers["bio"]
            if len(bio_value) > 1024:
                bio_value = bio_value[:1021] + "..."
            mod_embed.add_field(name="Character Biography", value=bio_value, inline=False)
            mod_embed.add_field(name="Position Applied For", value=answers["role"], inline=True)
            mod_embed.add_field(name="Roblox User ID", value=answers["roblox_id"], inline=True)
            mod_embed.add_field(name="Fictional SSN", value=ssn, inline=True)
            mod_embed.set_footer(text=f"Submitted by {user.display_name}")
            if portrait_url:
                mod_embed.set_image(url=portrait_url)
            mod_channel = self.bot.get_channel(MOD_CHANNEL_ID)
            if mod_channel:
                message = await mod_channel.send(content=user.mention, embed=mod_embed)
                # Add admin panel buttons for approve/deny
                class AdminPanel(discord.ui.View):
                    def __init__(self, user_id, message_id, timeout=604800):  # 7 days
                        super().__init__(timeout=timeout)
                        self.user_id = user_id
                        self.message_id = message_id
                    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
                    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
                        # Only allow admins to approve/deny
                        if not interaction.user.guild_permissions.manage_guild:
                            await interaction.response.send_message("You do not have permission to approve.", ephemeral=True)
                            return
                        guild = interaction.guild
                        member = guild.get_member(self.user_id)
                        # --- FIX: Always fetch member if not found in cache ---
                        if member is None:
                            try:
                                member = await guild.fetch_member(self.user_id)
                            except Exception as fetch_exc:
                                print(f"[FETCH MEMBER ERROR] Could not fetch member: {fetch_exc}")
                                member = None
                        # --- END FIX ---
                        if member:
                            role = guild.get_role(1338209827330986046)
                            if role:
                                await member.add_roles(role, reason="Character application approved")
                        try:
                            if member:
                                await member.send(embed=discord.Embed(
                                    title="Application Approved",
                                    description="Congratulations! Your character application has been approved and you have been whitelisted. Welcome aboard!",
                                    color=0x2ECC71
                                ))
                        except Exception as dm_exc:
                            print(f"[DM ERROR] Could not DM user: {dm_exc}")
                        # Upload character data to Firebase Firestore
                        if db:
                            try:
                                character_data = dict(answers)
                                character_data.update({
                                    'discord_id': str(self.user_id),
                                    'approved_at': firestore.SERVER_TIMESTAMP,
                                    'mod_message_id': str(self.message_id),
                                    'ssn': ssn  # Add formatted SSN to Firestore
                                })
                                if portrait_url:
                                    character_data['portrait_url'] = portrait_url  # Add portrait image link as text
                                db.collection('characters').document(str(self.user_id)).set(character_data)
                            except Exception as firebase_exc:
                                print(f"[FIREBASE ERROR] {firebase_exc}")
                        await interaction.response.send_message("Application approved, user notified, and data uploaded to Firebase.", ephemeral=True)
                        await interaction.message.edit(view=None)
                    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
                    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
                        if not interaction.user.guild_permissions.manage_guild:
                            await interaction.response.send_message("You do not have permission to deny.", ephemeral=True)
                            return
                        guild = interaction.guild
                        member = guild.get_member(self.user_id)
                        # --- FIX: Always fetch member if not found in cache ---
                        if member is None:
                            try:
                                member = await guild.fetch_member(self.user_id)
                            except Exception as fetch_exc:
                                print(f"[FETCH MEMBER ERROR] Could not fetch member: {fetch_exc}")
                                member = None
                        # --- END FIX ---
                        try:
                            if member:
                                await member.send(embed=discord.Embed(
                                    title="Application Denied",
                                    description="Your character application has been denied. Please await further messaging from an administrator for more information.",
                                    color=0xE74C3C
                                ))
                        except Exception as dm_exc:
                            print(f"[DM ERROR] Could not DM user: {dm_exc}")
                        await interaction.response.send_message("Application denied and user notified.", ephemeral=True)
                        await interaction.message.edit(view=None)
                admin_panel = AdminPanel(user.id, message.id)
                await message.edit(view=admin_panel)
                # Send success message to user after submission
                success_embed = discord.Embed(
                    title="Successfully Submitted",
                    description=(
                        "Your application has been successfully submitted to our panel of administrators. "
                        "Please allow up to 3 business days for careful review of your character.\n\n"
                        "In the meantime, feel free to check out the rest of the channels available for you at this time. "
                        "It is required that you review and agree to our <#1338209799505973399> as a member of the community. "
                        "Learn more about our commmunities mission in <#1338209811128516802> or our history in <#1338209804849643560>. "
                        "Your cooperation is appreciated."
                    ),
                    color=0x2ECC71
                )
                await user.send(embed=success_embed)
            else:
                error_embed = discord.Embed(
                    description="**Character Creation & Whitelist Application**\n\n⚠️ Mod channel not found! Please check the channel ID.",
                    color=0x1F3C72
                )
                await user.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                description=f"**Character Creation & Whitelist Application**\n\n❌ There was an error: {e}",
                color=0x1F3C72
            )
            try:
                await interaction.user.send(embed=error_embed)
            except:
                pass
            print(f"Error in DM character creation: {e}")

async def setup(bot):
    await bot.add_cog(Character(bot))
