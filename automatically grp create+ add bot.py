from pyrogram import Client, filters
from pyrogram.errors import FloodWait
import asyncio

# === CONFIG ===
API_ID = 28925121
API_HASH = "667bf87d3ce77e3e9f5bc4e62021c152"
STRING_SESSION = "BQG5XMEALefAG1tAh5rb_ixlDClgK3oVXNll0Zsy4KLYPv9oaAtud-bpgSjFacjOrkxXFm8rKiBP4LFDxnoMJjiLdydw79_uxghVYAgnCYLRx1SKxqmjqiK5vJDWZ41Adv939XotimnEvYMbcB5d-sFu29geQ9D9aKSeLow36eTAGHlXHzWlqhHWRojCE-HT5JAMSuSIAY6pQobamA31LRD1mWJGiKrHuHjBIFJ2AZ3bkfPwaNxplgH9WmOZ7xOj4yX6dCgLLmyki_WRY3NxSdH7kAoBDenooIW5CvStu9blX-UZsjvR0NMMZeIjVcqatZkB0Ua0LR49JlNVbA8y6ePTdDeF8QAAAAGkiA8rAA"
ESCROW_BOT_USERNAME = "@DemoEscrowerBot"  # with @
OWNER_ID = 6998916494  # integer

# === START CLIENT ===
app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)

async def ensure_peer(client, peer):
    """Send a dummy message to ensure peer exists in session."""
    try:
        if isinstance(peer, int):  # user id
            await client.send_message(peer, "Hello 👋 (peer setup)")
        elif isinstance(peer, str):  # username
            await client.send_message(peer, "/start")  # For bot
        await asyncio.sleep(1)
    except Exception as e:
        print(f"[Peer Setup Error] {peer} -> {e}")

@app.on_message(filters.private & filters.text)
async def create_group(client, message):
    trigger_words = ["deal", "/setup", "/create"]

    if any(word in message.text.lower() for word in trigger_words):
        try:
            buyer_username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
            chat_title = f"Escrow Deal - {message.from_user.first_name}"

            # Step 0: Ensure peers exist
            await ensure_peer(client, OWNER_ID)
            await ensure_peer(client, ESCROW_BOT_USERNAME)

            # Step 1: Create group with buyer + owner
            group = await client.create_group(chat_title, [OWNER_ID, message.from_user.id])

            # Step 2: Add escrow bot
            try:
                await client.add_chat_members(group.id, ESCROW_BOT_USERNAME)
            except Exception as bot_err:
                print(f"[Bot Add Error] {bot_err}")

            # Step 3: Send and pin form
            form_message = f"""
**DEAL INFO :**
**BUYER :** {buyer_username}
**SELLER :** @
**DEAL AMOUNT :** 10 rs
**TIME TO COMPLETE DEAL :**
"""
            sent_msg = await client.send_message(group.id, form_message)
            await client.pin_chat_message(group.id, sent_msg.id)

            # Step 4: Invite link
            link = await client.export_chat_invite_link(group.id)
            await message.reply_text(f"✅ New private escrow group created:\n🔗 {link}")

        except FloodWait as e:
            await asyncio.sleep(e.value)
            await message.reply_text("⏳ Please try again later, Telegram rate limit reached.")
        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}")
    else:
        await message.reply_text("Type 'deal' or '/setup' to create a new escrow group.")

print("🚀 Userbot running...")
app.run()
