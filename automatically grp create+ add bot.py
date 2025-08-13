from pyrogram import Client, filters
from pyrogram.errors import FloodWait
import time

# === CONFIG ===
API_ID = 26014459
API_HASH = "34b8791089c72367a5088f96d925f989"
STRING_SESSION = "BQG5XMEALefAG1tAh5rb_ixlDClgK3oVXNll0Zsy4KLYPv9oaAtud-bpgSjFacjOrkxXFm8rKiBP4LFDxnoMJjiLdydw79_uxghVYAgnCYLRx1SKxqmjqiK5vJDWZ41Adv939XotimnEvYMbcB5d-sFu29geQ9D9aKSeLow36eTAGHlXHzWlqhHWRojCE-HT5JAMSuSIAY6pQobamA31LRD1mWJGiKrHuHjBIFJ2AZ3bkfPwaNxplgH9WmOZ7xOj4yX6dCgLLmyki_WRY3NxSdH7kAoBDenooIW5CvStu9blX-UZsjvR0NMMZeIjVcqatZkB0Ua0LR49JlNVbA8y6ePTdDeF8QAAAAGkiA8rAA"
ESCROW_BOT_USERNAME = "DemoEscrowerBot"  # without @
OWNER_ID = 6998916494  # Apna Telegram user ID yaha daal

# === START CLIENT ===
app = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION
)

@app.on_message(filters.private & filters.text)
async def create_group(client, message):
    trigger_words = ["deal", "/setup", "/create"]

    if message.text.lower() in trigger_words:
        try:
            buyer_username = (
                f"@{message.from_user.username}" 
                if message.from_user.username 
                else message.from_user.first_name
            )

            chat_title = f"Escrow Deal - {message.from_user.first_name}"

            # Step 1: Create private supergroup
            group = await client.create_supergroup(chat_title, "Private escrow group auto-created")

            # Step 2: Add buyer
            await client.add_chat_members(group.id, message.from_user.id)

            # Step 3: Add owner
            await client.add_chat_members(group.id, OWNER_ID)

            # Step 4: Add escrow bot
            await client.add_chat_members(group.id, ESCROW_BOT_USERNAME)

            # Step 5: Send and pin the form
            form_message = f"""
**DEAL INFO :**
**BUYER :** @
**SELLER :** @
**DEAL AMOUNT :** 10 rs
**TIME TO COMPLETE DEAL :**
"""
            sent_msg = await client.send_message(group.id, form_message)
            await client.pin_chat_message(group.id, sent_msg.id)

            # Step 6: Send invite link to buyer
            link = await client.export_chat_invite_link(group.id)
            await message.reply_text(f"✅ New private escrow group created:\n🔗 {link}")

        except FloodWait as e:
            time.sleep(e.value)
            await message.reply_text("⏳ Please try again later, Telegram rate limit reached.")

        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}")

    else:
        await message.reply_text("Type 'deal' or '/setup' to create a new escrow group.")

print("🚀 Userbot running...")
app.run()
