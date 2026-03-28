import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()
MOD_CHANNEL_ID_STR = os.getenv("MOD_CHANNEL_ID")
MOD_CHANNEL_ID = int(MOD_CHANNEL_ID_STR) if MOD_CHANNEL_ID_STR else None

# Firebase initialization (run once per process)
FIREBASE_CRED_JSON = os.getenv("FIREBASE_CRED_JSON")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
db = None
if FIREBASE_CRED_JSON and FIREBASE_PROJECT_ID:
    try:
        import json
        cred_dict = json.loads(FIREBASE_CRED_JSON)
        cred = credentials.Certificate(cred_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'projectId': FIREBASE_PROJECT_ID
            })
        db = firestore.client()
        print("Firebase initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Firebase: {e}")
        db = None
else:
    print("Firebase credentials not provided, skipping initialization")

FORUM_CHANNEL_ID = 1486818607575863417

async def update_forum_thread(bot, user_id, character_data):
    """Update the forum thread embed with current character data"""
    try:
        if not db:
            return
        
        # Get character document to find forum thread ID
        character_ref = db.collection('characters').document(str(user_id))
        character_doc = character_ref.get()
        
        if not character_doc.exists:
            return
        
        char_data = character_doc.to_dict()
        forum_thread_id = char_data.get('forum_thread_id')
        
        if not forum_thread_id:
            return
        
        # Find forum channel and thread
        guild = None
        for g in bot.guilds:
            guild = g
            break
        
        if not guild:
            print("[FORUM UPDATE] Could not find guild")
            return
        
        forum_channel = guild.get_channel(FORUM_CHANNEL_ID)
        if not forum_channel:
            print(f"[FORUM UPDATE] Could not find forum channel {FORUM_CHANNEL_ID}")
            return
        
        try:
            thread = await guild.fetch_channel(int(forum_thread_id))
        except Exception as e:
            print(f"[FORUM UPDATE] Could not fetch thread {forum_thread_id}: {e}")
            return
        
        if not thread:
            print(f"[FORUM UPDATE] Thread {forum_thread_id} not found")
            return
        
        # Create updated embed
        character_name = character_data.get('full_name', f'Character {user_id}')
        updated_embed = discord.Embed(
            title=f"Approved Character: {character_name}",
            color=0x2ECC71
        )
        
        updated_embed.add_field(name="Full Legal Name", value=character_data.get('full_name', 'N/A'), inline=False)
        updated_embed.add_field(name="Date of Birth", value=character_data.get('dob', 'N/A'), inline=True)
        updated_embed.add_field(name="County", value=character_data.get('county', 'N/A'), inline=True)
        updated_embed.add_field(name="House District", value=character_data.get('house', 'N/A'), inline=True)
        updated_embed.add_field(name="Senate District", value=character_data.get('senate', 'N/A'), inline=True)
        updated_embed.add_field(name="Gender", value=character_data.get('gender', 'N/A'), inline=True)
        updated_embed.add_field(name="Political Party", value=character_data.get('party', 'N/A'), inline=True)
        updated_embed.add_field(name="Position Applied For", value=character_data.get('role', 'N/A'), inline=True)
        updated_embed.add_field(name="Roblox User ID", value=character_data.get('roblox_id', 'N/A'), inline=True)
        
        bio = character_data.get('bio', 'N/A')
        if len(bio) > 1024:
            bio = bio[:1021] + "..."
        updated_embed.add_field(name="Biography", value=bio, inline=False)
        
        portrait_url = character_data.get('portrait_url')
        if portrait_url:
            updated_embed.set_image(url=portrait_url)
        
        # Find and update the first message in the thread
        async for msg in thread.history(limit=1, oldest_first=True):
            try:
                await msg.edit(embed=updated_embed)
                print(f"✅ Updated forum thread {forum_thread_id} for user {user_id}")
            except Exception as edit_exc:
                print(f"[FORUM UPDATE ERROR] Could not edit message: {edit_exc}")
            break
        
    except Exception as e:
        print(f"[FORUM UPDATE ERROR] {e}")

class EditFieldModal(discord.ui.Modal):
    def __init__(self, field_name, title, user_id, character_data, collection_name="pending_applications", max_length=100, bot=None):
        super().__init__(title=title)
        self.field_name = field_name
        self.user_id = user_id
        self.character_data = character_data
        self.collection_name = collection_name
        self.bot = bot
        
        self.field_input = discord.ui.TextInput(
            label=f"New {field_name.replace('_', ' ').title()}",
            default=character_data.get(field_name, ''),
            max_length=max_length,
            required=True
        )
        self.add_item(self.field_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            new_value = str(self.field_input)
            self.character_data[self.field_name] = new_value
            
            # Save to database immediately
            if db:
                try:
                    doc_ref = db.collection(self.collection_name).document(self.user_id)
                    doc_ref.update({self.field_name: new_value})
                    await interaction.followup.send(f"✅ Updated {self.field_name} to: {new_value}", ephemeral=True)
                    
                    # Update forum thread if this is an approved character
                    if self.collection_name == "characters" and self.bot:
                        await update_forum_thread(self.bot, self.user_id, self.character_data)
                        
                except Exception as e:
                    await interaction.followup.send(f"❌ Error saving to database: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"✅ Updated {self.field_name} locally to: {new_value} (database not available)", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)

class EditPortraitModal(discord.ui.Modal):
    def __init__(self, user_id, character_data, collection_name="pending_applications", bot=None):
        super().__init__(title="Edit Portrait")
        self.user_id = user_id
        self.character_data = character_data
        self.collection_name = collection_name
        self.bot = bot
        
        self.portrait_url_input = discord.ui.TextInput(
            label="Portrait URL",
            default=character_data.get('portrait_url', ''),
            max_length=500,
            required=False,
            placeholder="Enter image URL or leave blank to keep current"
        )
        self.add_item(self.portrait_url_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            portrait_url = str(self.portrait_url_input).strip() if str(self.portrait_url_input).strip() else None
            
            if portrait_url:
                self.character_data['portrait_url'] = portrait_url
                
                # Save to database immediately
                if db:
                    try:
                        doc_ref = db.collection(self.collection_name).document(self.user_id)
                        doc_ref.update({'portrait_url': portrait_url})
                        await interaction.followup.send(f"✅ Portrait updated successfully!", ephemeral=True)
                        
                        # Update forum thread if this is an approved character
                        if self.collection_name == "characters" and self.bot:
                            await update_forum_thread(self.bot, self.user_id, self.character_data)
                            
                    except Exception as e:
                        await interaction.followup.send(f"❌ Error saving portrait to database: {str(e)}", ephemeral=True)
                else:
                    await interaction.followup.send(f"✅ Portrait updated locally (database not available)", ephemeral=True)
            else:
                await interaction.followup.send(f"⚠️ Portrait URL is required to update.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)

class EditDistrictsModal(discord.ui.Modal):
    def __init__(self, user_id, character_data, collection_name="pending_applications", bot=None):
        super().__init__(title="Edit Districts")
        self.user_id = user_id
        self.character_data = character_data
        self.collection_name = collection_name
        self.bot = bot
        
        self.house_input = discord.ui.TextInput(
            label="House District",
            default=character_data.get('house', ''),
            max_length=50,
            required=True
        )
        self.senate_input = discord.ui.TextInput(
            label="Senate District", 
            default=character_data.get('senate', ''),
            max_length=50,
            required=True
        )
        self.add_item(self.house_input)
        self.add_item(self.senate_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            house_value = str(self.house_input)
            senate_value = str(self.senate_input)
            
            self.character_data['house'] = house_value
            self.character_data['senate'] = senate_value
            
            # Save to database immediately
            if db:
                try:
                    doc_ref = db.collection(self.collection_name).document(self.user_id)
                    doc_ref.update({'house': house_value, 'senate': senate_value})
                    await interaction.followup.send(f"✅ Updated districts - House: {house_value}, Senate: {senate_value}", ephemeral=True)
                    
                    # Update forum thread if this is an approved character
                    if self.collection_name == "characters" and self.bot:
                        await update_forum_thread(self.bot, self.user_id, self.character_data)
                        
                except Exception as e:
                    await interaction.followup.send(f"❌ Error saving to database: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"✅ Updated districts locally (database not available)", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)

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
                ("role", "What position are you planning to apply for?", "e.g. Governor, House of Delegates", True),
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
                    await interaction_button.response.send_message(embed=discord.Embed(description="**Character Creation & Whitelist Application**\n\n✅ Your character has been submitted for review!", color=0x1F3C72))
                    self.stop()
                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
                async def cancel(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                    await interaction_button.response.send_message(embed=discord.Embed(description="**Character Creation & Whitelist Application**\n\n❌ Submission cancelled.", color=0x1F3C72))
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
                try:
                    # Store application data in pending collection first
                    pending_data = dict(answers)
                    pending_data.update({
                        'discord_id': str(user.id),
                        'submitted_at': firestore.SERVER_TIMESTAMP,
                        'user_mention': user.mention,
                        'username': user.display_name
                    })
                    if portrait_url:
                        pending_data['portrait_url'] = portrait_url

                    # Save to pending applications collection
                    if db:
                        try:
                            pending_ref = db.collection('pending_applications').document(str(user.id))
                            pending_ref.set(pending_data)
                            print(f"✅ Application saved to pending collection for user {user.id}")
                        except Exception as e:
                            print(f"❌ Failed to save pending application: {e}")
                    else:
                        print("⚠️ Firebase not available, application not saved to database")

                    # Create embed for mod review
                    mod_embed = discord.Embed(
                        title="🗳️ Pending Character Application",
                        description=f"**New application from {user.mention}**\n\nPlease review the application below and decide whether to approve or deny.",
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

                    message = await mod_channel.send(embed=mod_embed)
                    # Add admin panel buttons for approve/deny
                    class AdminPanel(discord.ui.View):
                        def __init__(self, user_id, message_id, timeout=604800):  # 7 days
                            super().__init__(timeout=timeout)
                            self.user_id = user_id
                            self.message_id = message_id
                        @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
                        async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
                            await interaction.response.defer(thinking=True)
                            try:
                                # Only allow admins to approve/deny
                                if not interaction.user.guild_permissions.manage_guild:
                                    await interaction.followup.send("You do not have permission to approve.", ephemeral=True)
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
                                    role = guild.get_role(1486597518954332283)
                                    if role:
                                        await member.add_roles(role, reason="Character application approved")
                                    # Set nickname to character full name
                                    try:
                                        character_name = character_data.get('full_name', '')
                                        if character_name:
                                            await member.edit(nick=character_name, reason="Character name set on approval")
                                    except Exception as nick_exc:
                                        print(f"[NICKNAME ERROR] Could not set nickname: {nick_exc}")
                                try:
                                    if member:
                                        await member.send(embed=discord.Embed(
                                            title="Application Approved",
                                            description="Congratulations! Your character application has been approved and you have been whitelisted. Welcome aboard!",
                                            color=0x2ECC71
                                        ))
                                except Exception as dm_exc:
                                    print(f"[DM ERROR] Could not DM user: {dm_exc}")
                                # Move from pending to approved collection
                                if db:
                                    try:
                                        pending_ref = db.collection('pending_applications').document(str(self.user_id))
                                        pending_doc = pending_ref.get()
                                        if pending_doc.exists:
                                            character_data = pending_doc.to_dict()
                                            # Generate SSN from Roblox ID
                                            roblox_id_raw = character_data.get('roblox_id', '')
                                            roblox_digits = ''.join(filter(str.isdigit, roblox_id_raw))
                                            roblox_digits = roblox_digits[-9:].rjust(9, '0')
                                            ssn = f"{roblox_digits[:3]}-{roblox_digits[3:5]}-{roblox_digits[5:]}"
                                            # Update with approval info
                                            character_data.update({
                                                'approved_at': firestore.SERVER_TIMESTAMP,
                                                'approved_by': str(interaction.user.id),
                                                'mod_message_id': str(self.message_id),
                                                'ssn': ssn  # Add formatted SSN to Firestore
                                            })
                                            # Move to main characters collection
                                            db.collection('characters').document(str(self.user_id)).set(character_data)
                                            # Delete from pending
                                            pending_ref.delete()
                                            print(f"✅ Application moved to characters collection for user {self.user_id}")
                                    except Exception as firebase_exc:
                                        print(f"[FIREBASE ERROR] {firebase_exc}")
                            
                            # Post approved character to forum channel
                            forum_channel_id = 1486818607575863417
                            forum_channel = interaction.guild.get_channel(forum_channel_id)
                            if forum_channel:
                                try:
                                    # Create forum post with character name as title
                                    character_name = character_data.get('full_name', f'Character {self.user_id}')
                                    
                                    # Create embed for the forum post
                                    forum_embed = discord.Embed(
                                        title=f"Approved Character: {character_name}",
                                        color=0x2ECC71
                                    )
                                    
                                    # Add character details
                                    forum_embed.add_field(name="Full Legal Name", value=character_data.get('full_name', 'N/A'), inline=False)
                                    forum_embed.add_field(name="Date of Birth", value=character_data.get('dob', 'N/A'), inline=True)
                                    forum_embed.add_field(name="County", value=character_data.get('county', 'N/A'), inline=True)
                                    forum_embed.add_field(name="House District", value=character_data.get('house', 'N/A'), inline=True)
                                    forum_embed.add_field(name="Senate District", value=character_data.get('senate', 'N/A'), inline=True)
                                    forum_embed.add_field(name="Gender", value=character_data.get('gender', 'N/A'), inline=True)
                                    forum_embed.add_field(name="Political Party", value=character_data.get('party', 'N/A'), inline=True)
                                    forum_embed.add_field(name="Position Applied For", value=character_data.get('role', 'N/A'), inline=True)
                                    forum_embed.add_field(name="Roblox User ID", value=character_data.get('roblox_id', 'N/A'), inline=True)
                                    
                                    # Add biography (truncated if too long)
                                    bio = character_data.get('bio', 'N/A')
                                    if len(bio) > 1024:
                                        bio = bio[:1021] + "..."
                                    forum_embed.add_field(name="Biography", value=bio, inline=False)
                                    
                                    # Add portrait if available
                                    portrait_url = character_data.get('portrait_url')
                                    if portrait_url:
                                        forum_embed.set_image(url=portrait_url)
                                    
                                    forum_embed.set_footer(text=f"Approved by {interaction.user.display_name} • User: {member.mention if member else 'Unknown'}")
                                    
                                    # Create the forum thread
                                    thread = await forum_channel.create_thread(
                                        name=character_name,
                                        embed=forum_embed
                                    )
                                    print(f"✅ Created forum thread for approved character: {character_name}")
                                    
                                    # Save forum thread ID to database
                                    if db:
                                        try:
                                            db.collection('characters').document(str(self.user_id)).update({
                                                'forum_thread_id': str(thread.id)
                                            })
                                            print(f"✅ Saved forum thread ID {thread.id} to database")
                                        except Exception as db_exc:
                                            print(f"[DATABASE ERROR] Could not save forum thread ID: {db_exc}")
                                    
                                except Exception as forum_exc:
                                    print(f"[FORUM ERROR] Could not create forum post: {forum_exc}")
                            
                                await interaction.followup.send("✅ Application approved, user notified, character posted to forum, and data moved to Firebase.", ephemeral=True)
                                await interaction.message.edit(view=None)
                            except Exception as e:
                                print(f"[APPROVE ERROR] {e}")
                                await interaction.followup.send(f"❌ Error during approval: {str(e)}", ephemeral=True)
                        @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
                        async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
                            await interaction.response.defer(thinking=True)
                            try:
                                if not interaction.user.guild_permissions.manage_guild:
                                    await interaction.followup.send("You do not have permission to deny.", ephemeral=True)
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
                                # Delete from pending applications
                                if db:
                                    try:
                                        pending_ref = db.collection('pending_applications').document(str(self.user_id))
                                        pending_ref.delete()
                                        print(f"✅ Pending application deleted for user {self.user_id}")
                                    except Exception as firebase_exc:
                                        print(f"[FIREBASE ERROR] {firebase_exc}")
                                await interaction.followup.send("✅ Application denied and user notified.", ephemeral=True)
                                await interaction.message.edit(view=None)
                            except Exception as e:
                                print(f"[DENY ERROR] {e}")
                                await interaction.followup.send(f"❌ Error during denial: {str(e)}", ephemeral=True)
                    admin_panel = AdminPanel(user.id, message.id)
                    await message.edit(view=admin_panel)
                    # Send success message to user after submission
                    success_embed = discord.Embed(
                        title="Application Submitted for Review",
                        description=(
                            "Your character application has been successfully submitted and is now pending review by our administrators. "
                            "Please allow up to 3 business days for careful review of your character.\n\n"
                            "In the meantime, feel free to check out the rest of the channels available for you at this time. "
                            "It is required that you review and agree to our <#1486597519504048301> as a member of the community. "
                            "Learn more about our commmunities mission in <#1486597519504048302> or our history in <#1486597519504048304>. "
                            "Your cooperation is appreciated."
                        ),
                        color=0x2ECC71
                    )
                    await user.send(embed=success_embed)
                except Exception as e:
                    print(f"Error sending to mod channel: {e}")
                    error_embed = discord.Embed(
                        description=f"**Character Creation & Whitelist Application**\n\n❌ There was an error submitting to mod channel: {str(e)}",
                        color=0x1F3C72
                    )
                    await user.send(embed=error_embed)
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

    @app_commands.command(name="pending_apps", description="View pending character applications (Admin only)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def pending_apps(self, interaction: discord.Interaction):
        """View all pending character applications"""
        global db
        if db is None:
            await interaction.response.send_message("Database not available - attempting to reinitialize...", ephemeral=True)
            # Try to reinitialize Firebase if it's not available
            try:
                if FIREBASE_CRED_JSON and FIREBASE_PROJECT_ID:
                    import json
                    cred_dict = json.loads(FIREBASE_CRED_JSON)
                    cred = credentials.Certificate(cred_dict)
                    if not firebase_admin._apps:
                        firebase_admin.initialize_app(cred, {
                            'projectId': FIREBASE_PROJECT_ID
                        })
                    db = firestore.client()
                    print("Firebase reinitialized successfully in pending_apps")
                    await interaction.followup.send("Database reinitialized successfully! Please try the command again.", ephemeral=True)
                else:
                    await interaction.followup.send("Database not available - Firebase credentials not configured.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Database not available - Firebase initialization failed: {str(e)}", ephemeral=True)
            return

        try:
            pending_ref = db.collection('pending_applications')
            pending_docs = pending_ref.stream()

            pending_list = []
            for doc in pending_docs:
                data = doc.to_dict()
                pending_list.append(f"• {data.get('username', 'Unknown')} ({doc.id}) - Submitted {data.get('submitted_at', 'Unknown time')}")

            if not pending_list:
                embed = discord.Embed(
                    title="Pending Applications",
                    description="No pending applications at this time.",
                    color=0x1F3C72
                )
            else:
                embed = discord.Embed(
                    title="Pending Applications",
                    description="\n".join(pending_list[:10]),  # Limit to 10 for embed size
                    color=0x1F3C72
                )
                if len(pending_list) > 10:
                    embed.set_footer(text=f"And {len(pending_list) - 10} more...")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Error retrieving pending applications: {e}", ephemeral=True)
    @app_commands.command(name="edit_pending", description="Edit a pending character application (Admin only)")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(user_id="The Discord user ID of the pending application to edit")
    async def edit_pending(self, interaction: discord.Interaction, user_id: str):
        """Edit a pending character application"""
        if not db:
            await interaction.response.send_message("Database not available.", ephemeral=True)
            return

        try:
            pending_ref = db.collection('pending_applications').document(user_id)
            pending_doc = pending_ref.get()
            
            if not pending_doc.exists:
                await interaction.response.send_message(f"No pending application found for user ID: {user_id}", ephemeral=True)
                return
            
            character_data = pending_doc.to_dict()
            
            # Create embed showing current data
            edit_embed = discord.Embed(
                title=f"Editing Pending Application - {character_data.get('username', 'Unknown')}",
                description="Use the buttons below to modify character fields:",
                color=0xF39C12
            )
            
            edit_embed.add_field(name="Full Name", value=character_data.get('full_name', 'Not set'), inline=True)
            edit_embed.add_field(name="DOB", value=character_data.get('dob', 'Not set'), inline=True)
            edit_embed.add_field(name="County", value=character_data.get('county', 'Not set'), inline=True)
            edit_embed.add_field(name="House District", value=character_data.get('house', 'Not set'), inline=True)
            edit_embed.add_field(name="Senate District", value=character_data.get('senate', 'Not set'), inline=True)
            edit_embed.add_field(name="Gender", value=character_data.get('gender', 'Not set'), inline=True)
            edit_embed.add_field(name="Party", value=character_data.get('party', 'Not set'), inline=True)
            edit_embed.add_field(name="Role", value=character_data.get('role', 'Not set'), inline=True)
            edit_embed.add_field(name="Roblox ID", value=character_data.get('roblox_id', 'Not set'), inline=True)
            
            bio = character_data.get('bio', 'Not set')
            if len(bio) > 100:
                bio = bio[:97] + "..."
            edit_embed.add_field(name="Biography", value=bio, inline=False)
            
            class EditPendingView(discord.ui.View):
                def __init__(self, bot, timeout=600):
                    super().__init__(timeout=timeout)
                    self.user_id = user_id
                    self.character_data = character_data
                    self.bot = bot
                    
                @discord.ui.button(label="Edit Name", style=discord.ButtonStyle.primary)
                async def edit_name(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditFieldModal("full_name", "Edit Full Name", self.user_id, self.character_data, "pending_applications", bot=self.bot))
                
                @discord.ui.button(label="Edit DOB", style=discord.ButtonStyle.primary)
                async def edit_dob(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditFieldModal("dob", "Edit Date of Birth (MM/DD/YYYY)", self.user_id, self.character_data, "pending_applications", bot=self.bot))
                
                @discord.ui.button(label="Edit County", style=discord.ButtonStyle.primary)
                async def edit_county(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditFieldModal("county", "Edit County", self.user_id, self.character_data, "pending_applications", bot=self.bot))
                
                @discord.ui.button(label="Edit Districts", style=discord.ButtonStyle.primary)
                async def edit_districts(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditDistrictsModal(self.user_id, self.character_data, "pending_applications", bot=self.bot))
                
                @discord.ui.button(label="Edit Bio", style=discord.ButtonStyle.secondary)
                async def edit_bio(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditFieldModal("bio", "Edit Biography", self.user_id, self.character_data, "pending_applications", max_length=1000, bot=self.bot))
                
                @discord.ui.button(label="Edit Portrait", style=discord.ButtonStyle.secondary)
                async def edit_portrait(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditPortraitModal(self.user_id, self.character_data, "pending_applications", bot=self.bot))
                
                @discord.ui.button(label="Close Editor", style=discord.ButtonStyle.secondary)
                async def close_editor(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_message("Character editor closed.", ephemeral=True)
                    await interaction.message.edit(view=None)
            
            await interaction.response.send_message(embed=edit_embed, view=EditPendingView(self.bot), ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"Error editing pending application: {str(e)}", ephemeral=True)

    @app_commands.command(name="edit_character", description="Edit an approved character (Admin only)")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(user_id="The Discord user ID of the approved character to edit")
    async def edit_character(self, interaction: discord.Interaction, user_id: str):
        """Edit an approved character"""
        if not db:
            await interaction.response.send_message("Database not available.", ephemeral=True)
            return

        try:
            character_ref = db.collection('characters').document(user_id)
            character_doc = character_ref.get()
            
            if not character_doc.exists:
                await interaction.response.send_message(f"No approved character found for user ID: {user_id}", ephemeral=True)
                return
            
            character_data = character_doc.to_dict()
            
            # Create embed showing current data
            edit_embed = discord.Embed(
                title=f"Editing Approved Character - {character_data.get('username', 'Unknown')}",
                description="Use the buttons below to modify character fields:",
                color=0x3498DB
            )
            
            edit_embed.add_field(name="Full Name", value=character_data.get('full_name', 'Not set'), inline=True)
            edit_embed.add_field(name="DOB", value=character_data.get('dob', 'Not set'), inline=True)
            edit_embed.add_field(name="County", value=character_data.get('county', 'Not set'), inline=True)
            edit_embed.add_field(name="House District", value=character_data.get('house', 'Not set'), inline=True)
            edit_embed.add_field(name="Senate District", value=character_data.get('senate', 'Not set'), inline=True)
            edit_embed.add_field(name="Gender", value=character_data.get('gender', 'Not set'), inline=True)
            edit_embed.add_field(name="Party", value=character_data.get('party', 'Not set'), inline=True)
            edit_embed.add_field(name="Role", value=character_data.get('role', 'Not set'), inline=True)
            edit_embed.add_field(name="Roblox ID", value=character_data.get('roblox_id', 'Not set'), inline=True)
            
            bio = character_data.get('bio', 'Not set')
            if len(bio) > 100:
                bio = bio[:97] + "..."
            edit_embed.add_field(name="Biography", value=bio, inline=False)
            
            class EditCharacterView(discord.ui.View):
                def __init__(self, bot, timeout=600):
                    super().__init__(timeout=timeout)
                    self.user_id = user_id
                    self.character_data = character_data
                    self.bot = bot
                    
                @discord.ui.button(label="Edit Name", style=discord.ButtonStyle.primary)
                async def edit_name(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditFieldModal("full_name", "Edit Full Name", self.user_id, self.character_data, "characters", bot=self.bot))
                
                @discord.ui.button(label="Edit DOB", style=discord.ButtonStyle.primary)
                async def edit_dob(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditFieldModal("dob", "Edit Date of Birth (MM/DD/YYYY)", self.user_id, self.character_data, "characters", bot=self.bot))
                
                @discord.ui.button(label="Edit County", style=discord.ButtonStyle.primary)
                async def edit_county(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditFieldModal("county", "Edit County", self.user_id, self.character_data, "characters", bot=self.bot))
                
                @discord.ui.button(label="Edit Districts", style=discord.ButtonStyle.primary)
                async def edit_districts(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditDistrictsModal(self.user_id, self.character_data, "characters", bot=self.bot))
                
                @discord.ui.button(label="Edit Bio", style=discord.ButtonStyle.secondary)
                async def edit_bio(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditFieldModal("bio", "Edit Biography", self.user_id, self.character_data, "characters", max_length=1000, bot=self.bot))
                
                @discord.ui.button(label="Edit Portrait", style=discord.ButtonStyle.secondary)
                async def edit_portrait(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_modal(EditPortraitModal(self.user_id, self.character_data, "characters", bot=self.bot))
                
                @discord.ui.button(label="Close Editor", style=discord.ButtonStyle.secondary)
                async def close_editor(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_message("Character editor closed.", ephemeral=True)
                    await interaction.message.edit(view=None)
            
            await interaction.response.send_message(embed=edit_embed, view=EditCharacterView(self.bot), ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"Error editing character: {str(e)}", ephemeral=True)

    @app_commands.command(name="approve_id", description="Approve a character application by user ID (Admin only)")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(user_id="The Discord user ID of the application to approve")
    async def approve_id(self, interaction: discord.Interaction, user_id: str):
        """Approve a character application by user ID"""
        await interaction.response.defer(thinking=True)
        try:
            if not db:
                await interaction.followup.send("Database not available.", ephemeral=True)
                return
            # Get pending application
            pending_ref = db.collection('pending_applications').document(user_id)
            pending_doc = pending_ref.get()
            
            if not pending_doc.exists:
                await interaction.response.send_message(f"No pending application found for user ID: {user_id}", ephemeral=True)
                return
            
            character_data = pending_doc.to_dict()
            
            # Get the guild member
            guild = interaction.guild
            member = guild.get_member(int(user_id))
            if member is None:
                try:
                    member = await guild.fetch_member(int(user_id))
                except Exception as fetch_exc:
                    print(f"[FETCH MEMBER ERROR] Could not fetch member: {fetch_exc}")
                    member = None
            
            # Add role if member exists
            if member:
                role = guild.get_role(1486597518954332283)  # Whitelist role
                if role:
                    await member.add_roles(role, reason="Character application approved via /approve_id")
                
                # DM the user
                try:
                    await member.send(embed=discord.Embed(
                        title="Application Approved",
                        description="Congratulations! Your character application has been approved and you have been whitelisted. Welcome aboard!",
                        color=0x2ECC71
                    ))
                except Exception as dm_exc:
                    print(f"[DM ERROR] Could not DM user: {dm_exc}")
                
                # Set nickname to character full name
                try:
                    character_name = character_data.get('full_name', '')
                    if character_name:
                        await member.edit(nick=character_name, reason="Character name set on approval")
                except Exception as nick_exc:
                    print(f"[NICKNAME ERROR] Could not set nickname: {nick_exc}")
            
            # Generate SSN from Roblox ID
            roblox_id_raw = character_data.get('roblox_id', '')
            roblox_digits = ''.join(filter(str.isdigit, roblox_id_raw))
            roblox_digits = roblox_digits[-9:].rjust(9, '0')
            ssn = f"{roblox_digits[:3]}-{roblox_digits[3:5]}-{roblox_digits[5:]}"
            
            # Move to approved collection
            character_data.update({
                'approved_at': firestore.SERVER_TIMESTAMP,
                'approved_by': str(interaction.user.id),
                'ssn': ssn
            })
            
            db.collection('characters').document(user_id).set(character_data)
            pending_ref.delete()
            
            # Create forum thread
            forum_channel_id = 1486818607575863417
            forum_channel = interaction.guild.get_channel(forum_channel_id)
            if forum_channel:
                try:
                    character_name = character_data.get('full_name', f'Character {user_id}')
                    
                    forum_embed = discord.Embed(
                        title=f"Approved Character: {character_name}",
                        color=0x2ECC71
                    )
                    
                    forum_embed.add_field(name="Full Legal Name", value=character_data.get('full_name', 'N/A'), inline=False)
                    forum_embed.add_field(name="Date of Birth", value=character_data.get('dob', 'N/A'), inline=True)
                    forum_embed.add_field(name="County", value=character_data.get('county', 'N/A'), inline=True)
                    forum_embed.add_field(name="House District", value=character_data.get('house', 'N/A'), inline=True)
                    forum_embed.add_field(name="Senate District", value=character_data.get('senate', 'N/A'), inline=True)
                    forum_embed.add_field(name="Gender", value=character_data.get('gender', 'N/A'), inline=True)
                    forum_embed.add_field(name="Political Party", value=character_data.get('party', 'N/A'), inline=True)
                    forum_embed.add_field(name="Position Applied For", value=character_data.get('role', 'N/A'), inline=True)
                    forum_embed.add_field(name="Roblox User ID", value=character_data.get('roblox_id', 'N/A'), inline=True)
                    
                    bio = character_data.get('bio', 'N/A')
                    if len(bio) > 1024:
                        bio = bio[:1021] + "..."
                    forum_embed.add_field(name="Biography", value=bio, inline=False)
                    
                    portrait_url = character_data.get('portrait_url')
                    if portrait_url:
                        forum_embed.set_image(url=portrait_url)
                    
                    forum_embed.set_footer(text=f"Approved by {interaction.user.display_name} • User: {member.mention if member else 'Unknown'}")
                    
                    thread = await forum_channel.create_thread(
                        name=character_name,
                        embed=forum_embed
                    )
                    
                    # Save forum thread ID
                    db.collection('characters').document(user_id).update({
                        'forum_thread_id': str(thread.id)
                    })
                    
                    print(f"✅ Created forum thread for approved character: {character_name}")
                    
                except Exception as forum_exc:
                    print(f"[FORUM ERROR] Could not create forum post: {forum_exc}")
            
            await interaction.followup.send(f"✅ Successfully approved character application for user {user_id}!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error approving application: {str(e)}", ephemeral=True)
            print(f"[APPROVE_ID ERROR] {e}")

    @app_commands.command(name="deny_id", description="Deny a character application by user ID (Admin only)")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(user_id="The Discord user ID of the application to deny")
    async def deny_id(self, interaction: discord.Interaction, user_id: str):
        """Deny a character application by user ID"""
        await interaction.response.defer(thinking=True)
        try:
            if not db:
                await interaction.followup.send("Database not available.", ephemeral=True)
                return
            # Get pending application
            pending_ref = db.collection('pending_applications').document(user_id)
            pending_doc = pending_ref.get()
            
            if not pending_doc.exists:
                await interaction.response.send_message(f"No pending application found for user ID: {user_id}", ephemeral=True)
                return
            
            # Get the guild member
            guild = interaction.guild
            member = guild.get_member(int(user_id))
            if member is None:
                try:
                    member = await guild.fetch_member(int(user_id))
                except Exception as fetch_exc:
                    print(f"[FETCH MEMBER ERROR] Could not fetch member: {fetch_exc}")
                    member = None
            
            # DM the user about denial
            if member:
                try:
                    await member.send(embed=discord.Embed(
                        title="Application Denied",
                        description="Your character application has been denied. Please await further messaging from an administrator for more information.",
                        color=0xE74C3C
                    ))
                except Exception as dm_exc:
                    print(f"[DM ERROR] Could not DM user: {dm_exc}")
            
            # Delete from pending applications
            pending_ref.delete()
            
            await interaction.followup.send(f"✅ Successfully denied character application for user {user_id}!", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error denying application: {str(e)}", ephemeral=True)
            print(f"[DENY_ID ERROR] {e}")

async def setup(bot):
    await bot.add_cog(Character(bot))
