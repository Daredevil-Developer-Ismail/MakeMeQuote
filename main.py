import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, CallbackContext
import io
import uuid
from PIL import Image, ImageDraw, ImageFont, ImageOps

botUsername = "@MakeMeQuote_bot";
file_id_cache = {}
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! I'm your bot. How can I help you?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the message text

    if update.message.chat.type in ['group', 'supergroup']:

        if botUsername in update.message.text:

            if update.message.reply_to_message:

                replied_user = update.message.reply_to_message.from_user
                progress = await update.message.reply_text("5% Complete");
                # Fetch the user's profile photos
                user_profile_photos = await context.bot.get_user_profile_photos(replied_user.id)

                # Check if the user has any profile photos
                if user_profile_photos.total_count > 0:
                    # Get the main (current) profile photo, usually the highest resolution of the first photo
                    main_photo = user_profile_photos.photos[0][-1]
                    photo_file = await main_photo.get_file()

                    short_id = str(uuid.uuid4())[:8]  # 8-character unique ID
                    file_id_cache[short_id] = photo_file.file_id
                    # Download and open the profile photo
                    photo_bytes = await photo_file.download_as_bytearray()
                    profile_img = Image.open(io.BytesIO(photo_bytes))

                    # Convert profile picture to grayscale and ensure RGBA mode
                    profile_img = ImageOps.grayscale(profile_img).convert("RGBA")

                    # Define fonts: larger font for the main quote and smaller italic font for the username
                    quote_font = ImageFont.truetype("Montserrat-Medium.ttf", 30)  # Main quote font
                    username_font = ImageFont.truetype("Montserrat-Italic.ttf", 20)  # Italic font for the username
                    bot_font = ImageFont.truetype("Montserrat-Italic.ttf", 10)

                    # Define the quote text and username text
                    quote_text = update.message.reply_to_message.text
                    username_text = f'- @{replied_user.username} ~{replied_user.full_name}'

                    if not quote_text:

                        return
                    # Measure text dimensions to determine background size

                    dummy_image = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(dummy_image)
                    quote_bbox = draw.textbbox((0, 0), quote_text, font=quote_font)
                    username_bbox = draw.textbbox((0, 0), username_text, font=username_font)
                    quote_width = quote_bbox[2] - quote_bbox[0]
                    username_width = username_bbox[2] - username_bbox[0]
                    text_height = quote_bbox[3] - quote_bbox[1] + username_bbox[3] - username_bbox[1]

                    # Define padding and overlay size
                    padding = 40
                    overlay_width = 300  # Width of the profile overlay on the left side

                    # Calculate overall background dimensions
                    background_width = max(quote_width, username_width) + overlay_width + 3 * padding
                    background_height = max(text_height, overlay_width) + 2 * padding

                    # Create black background
                    background = Image.new('RGBA', (background_width, background_height), (0, 0, 0, 255))

                    # Resize and apply fade to the profile picture
                    profile_img = profile_img.resize((overlay_width, background_height - 2 * 0))

                    # Create a gradient mask to fade the right side of the profile picture
                    gradient = Image.new('L', (overlay_width, profile_img.height), color=1)
                    for x in range(overlay_width):
                        # Gradually make pixels more transparent towards the right
                        opacity = int(300 * (1 - x / overlay_width))
                        for y in range(profile_img.height):
                            gradient.putpixel((x, y), opacity)
                    profile_img.putalpha(gradient)  # Apply gradient as an alpha mask

                    await progress.edit_text("50% Complete");

                    # Paste the faded profile image onto the background
                    overlay_x = 0
                    overlay_y = (background_height - profile_img.height) // 2
                    background.paste(profile_img, (overlay_x, overlay_y), profile_img)

                    # Draw the quote text on the right side of the profile image
                    draw = ImageDraw.Draw(background)
                    quote_x_position = overlay_x + overlay_width + padding
                    quote_y_position = (background_height - text_height) // 2

                    # Draw the main quote text
                    draw.text((quote_x_position, quote_y_position), quote_text, fill="white", font=quote_font)

                    # Draw the smaller italic username text below the main quote
                    username_y_position = quote_y_position + quote_bbox[3] - quote_bbox[
                        1] + 10  # Small spacing below quote
                    draw.text((quote_x_position, username_y_position+10), username_text, fill="white", font=username_font)
                    draw.text((background_width-(padding*10), background_height - padding), botUsername, fill="white",
                              font=bot_font)

                    # Save to bytes and send
                    await progress.edit_text("99% Complete")
                    output = io.BytesIO()
                    background.save(output, format="PNG")
                    output.seek(0)

                    reply_markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton(text="🎨", callback_data=f"COLOR+{short_id}+{username_text}"),
                        InlineKeyboardButton(text="🔁", callback_data=f"MOVE+{short_id}+{username_text}")]
                    ])
                    print(f"COLOR+{short_id}+{quote_text}+{username_text}")
                    await progress.delete()
                    await update.message.reply_photo(photo=output, caption=f"> {quote_text}", reply_markup=reply_markup, parse_mode="MarkdownV2")



async def handle_callback(update: Update, context: CallbackContext):

    callback = update.callback_query

    await callback.answer()

    data = callback.data
    if data.startswith("COLOR+"):
        short_id = data.split("+")[1]
        file_id = file_id_cache.get(short_id)

        progress = await update.callback_query.message.reply_text("5% Complete")
        if file_id:

            photo_file = await context.bot.get_file(file_id)
            photo_bytes = await photo_file.download_as_bytearray()

            photo_bytes = await photo_file.download_as_bytearray()
            profile_img = Image.open(io.BytesIO(photo_bytes))

            if callback.message.reply_markup.inline_keyboard[0][0].text == '🎨':
                profile_img = profile_img.convert("RGB")  # Convert back to color
            else:  # Image is color
                profile_img = ImageOps.grayscale(profile_img)  # Convert to grayscale

            button_text_for_coloring = "";

            if callback.message.reply_markup.inline_keyboard[0][0].text == '🎨':

                button_text_for_coloring = "🔘"

            else:

                button_text_for_coloring = '🎨'

            await progress.edit_text("50% Complete")
            quote_font = ImageFont.truetype("Montserrat-Medium.ttf", 30)  # Main quote font
            username_font = ImageFont.truetype("Montserrat-Italic.ttf", 20)  # Italic font for the username
            bot_font = ImageFont.truetype("Montserrat-Italic.ttf", 10)

            # Define the quote text and username text
            # quote_text = data.split("+")[2]
            quote_text = callback.message.caption;
            username_text = f'{data.split("+")[2]}'

            if not quote_text:
                return

            dummy_image = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
            draw = ImageDraw.Draw(dummy_image)
            quote_bbox = draw.textbbox((0, 0), quote_text, font=quote_font)
            username_bbox = draw.textbbox((0, 0), username_text, font=username_font)
            quote_width = quote_bbox[2] - quote_bbox[0]
            username_width = username_bbox[2] - username_bbox[0]
            text_height = quote_bbox[3] - quote_bbox[1] + username_bbox[3] - username_bbox[1]

            padding = 40
            overlay_width = 300  # Width of the profile overlay on the left side

            # Calculate overall background dimensions
            background_width = max(quote_width, username_width) + overlay_width + 3 * padding
            background_height = max(text_height, overlay_width) + 2 * padding

            # Create black background
            background = Image.new('RGBA', (background_width, background_height), (0, 0, 0, 255))

            # Resize and apply fade to the profile picture
            profile_img = profile_img.resize((overlay_width, background_height - 2 * 0))

            # Create a gradient mask to fade the right side of the profile picture
            gradient = Image.new('L', (overlay_width, profile_img.height), color=255)
            for x in range(overlay_width):
                # Gradually make pixels more transparent towards the right
                opacity = int(300 * (1 - x / overlay_width))
                for y in range(profile_img.height):
                    gradient.putpixel((x, y), opacity)

            profile_img.putalpha(gradient)  # Apply gradient as an alpha mask

            # Paste the faded profile image onto the background
            overlay_x = 0
            overlay_y = (background_height - profile_img.height) // 2
            background.paste(profile_img, (overlay_x, overlay_y), profile_img)

            # Draw the quote text on the right side of the profile image
            draw = ImageDraw.Draw(background)
            quote_x_position = overlay_x + overlay_width + padding
            quote_y_position = (background_height - text_height) // 2

            # Draw the main quote text
            draw.text((quote_x_position, quote_y_position), quote_text, fill="white", font=quote_font)

            # Draw the smaller italic username text below the main quote
            username_y_position = quote_y_position + quote_bbox[3] - quote_bbox[
                1] + 10  # Small spacing below quote
            draw.text((quote_x_position, username_y_position + 10), username_text, fill="white", font=username_font)
            draw.text((background_width - (padding * 10), background_height - padding), botUsername, fill="white",
                      font=bot_font)

            await progress.edit_text("99% Complete")
            # Save to bytes and send
            output = io.BytesIO()
            background.save(output, format="PNG")
            output.seek(0)

            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton(text=f"{button_text_for_coloring}", callback_data=f"COLOR+{short_id}+{username_text}"),
                InlineKeyboardButton(text="🔁", callback_data=f"MOVE+{short_id}+{username_text}")]
            ])

            await progress.delete()
            await update.callback_query.message.reply_photo(photo=output, reply_markup=reply_markup)



# Main function to run the bot
def main():
    # Initialize the Application with your bot's token
    application = Application.builder().token('7906692925:AAHN5MyTuwSTXQXx5nwX7sQnIY55QgFtJrU').build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    application.run_polling()


if __name__ == '__main__':
    main()
