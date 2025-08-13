from pyrogram import Client, filters
from pyrogram.types import Message

# ===== CONFIG =====
API_ID = 26014459
API_HASH = "34b8791089c72367a5088f96d925f989"
STRING_SESSION = "BQGM8vsAJVppG5SfjCvycz5l9o_UIsYpj3bvjYYF7qxZijHTM8_7mx8HlI2NVksjHXC3o31_QhFdq3VQGp510kRTE8CP0lYNSxQoM7A00-Wa56JNH1R2cNWTDuUGTYXqbif1B4z96_vPRJvPysL-R-6YMO7BDrI39Poyxv-IieogpMorJKUiQEgn1DjbeQTQNkpbJNwa2l-sbXumBfw5zwMCCZo4-iW_cNULOJLR_hw9-cRC64tMvegiJUUxmpweOThIJdz4ElEl7_qWV1HJSuTkPHyO_RaAIem-GwqQEi5RUlfpKXkCcOZYkPzZpMyrymLzcD0c-cGjPY7lqvFatJnNxF__VwAAAAGx20OoAA"

OWNER_ID = 6998916494  # Tumhara Owner ID

app = Client(
    name="broadcast_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION
)

@app.on_message(filters.command("brodcast") & filters.user(OWNER_ID))
async def broadcast(_, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/brodcast your_message_here`", quote=True)

    text = message.text.split(" ", 1)[1]
    sent_count = 0
    failed_count = 0

    async for dialog in app.get_dialogs():
        try:
            await app.send_message(dialog.chat.id, text)
            sent_count += 1
        except Exception:
            failed_count += 1

    await message.reply(f"✅ Broadcast Done!\nSent: {sent_count}\nFailed: {failed_count}", quote=True)

print("✅ Userbot Started!")
app.run()
