from pyrogram import Client, filters
from pyrogram.types import Message
from config import auth_users, sudo_users

@Client.on_message(filters.command("auth"))
async def auth_command(client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is admin
    if user_id not in auth_users:
        await message.reply("❌ You are not authorized to use this command.")
        return
    
    try:
        # Get the user ID to authorize
        target_user_id = int(message.text.split()[1])
        sudo_users.append(target_user_id)
        await message.reply(f"✅ User {target_user_id} has been authorized to use the bot!")
    except (IndexError, ValueError):
        await message.reply("❌ Usage: /auth user_id")

@Client.on_message(filters.command("users"))
async def list_users(client, message: Message):
    user_id = message.from_user.id
    if user_id not in auth_users:
        await message.reply("❌ You are not authorized to use this command.")
        return
    
    users_list = "\n".join([str(uid) for uid in sudo_users])
    await message.reply(f"Authorized Users:\n{users_list}")