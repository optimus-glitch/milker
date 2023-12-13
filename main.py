import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TELEGRAM_BOT_TOKEN = "6828435487:AAFfzO-B-IU-QF7X5EEQEDDkdUX0r9S08Ck"

# Directories to save files
UPLOADS_DIR = "uploads"
OUTPUTS_DIR = "outputs"

for directory in [UPLOADS_DIR, OUTPUTS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Set to store processed file names
processed_files = set()

# Set to store processed domains
processed_domains = set()

# Global variables for concurrent processing
file_queue = []
processing_now = False
executor = None  # Declare executor as a global variable

ALLOWED_USER_IDS = {1187810967, 6023294627, 5577750831, 6687123929}

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Welcome to Subdomain Enumeration Bot!\nSend me a file with domains or a single domain to get started.'
    )

def process_file(file_entry, context: CallbackContext) -> None:
    try:
        # Run subdomain enumeration script
        file_name = file_entry["file_name"]
        chat_id = file_entry["chat_id"]
        output_file_name = f"{file_name.split('.')[0]}_sub-domains.txt"
        output_file_path = os.path.join(OUTPUTS_DIR, output_file_name)

        # Read domains from the file
        with open(os.path.join(UPLOADS_DIR, file_name), 'r') as file:
            domains = file.read().splitlines()

        # Filter out already processed domains
        new_domains = list(set(domains) - processed_domains)

        if not new_domains:
            context.bot.send_message(chat_id, "No new domains to process.")
            return

        subprocess.check_call([
            'subfinder', '-dL',
            os.path.join(UPLOADS_DIR, file_name), '-o', output_file_path
        ])

        # Send results back to the user
        context.bot.send_document(chat_id, document=open(output_file_path, 'rb'))

        # Update the processed domains set
        processed_domains.update(new_domains)

        # Delete the uploaded and output files
        os.remove(os.path.join(UPLOADS_DIR, file_name))
        os.remove(output_file_path)

    except Exception as e:
        context.bot.send_message(chat_id, f"Error during enumeration: {e}")
        print(f"Error during enumeration: {e}")

    finally:
        # Process the next file in the queue (if any)
        process_file_queue(context)

def process_file_queue(context: CallbackContext) -> None:
    global processing_now
    if file_queue:
        # Dequeue the first file in the queue
        file_entry = file_queue.pop(0)

        # Use the ThreadPoolExecutor to run file processing concurrently
        executor.submit(process_file, file_entry, context)

def handle_document(update: Update, context: CallbackContext) -> None:
    global processing_now
    file_id = update.message.document.file_id
    file_name = update.message.document.file_name
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if user_id not in ALLOWED_USER_IDS:
        context.bot.send_message(
            chat_id, "You are not authorized to use this bot.")
        return

    # Check if the file name has already been processed
    if file_name in [entry["file_name"] for entry in file_queue]:
        context.bot.send_message(
            chat_id, f"You have already uploaded the file '{file_name}'.")
        return

    file = context.bot.get_file(file_id)

    # Generate a unique filename based on the original file name
    unique_filename = file_name
    upload_file_path = os.path.join(UPLOADS_DIR, unique_filename)

    try:
        # Download the file to the "uploads" folder
        file.download(upload_file_path)

        # Send a message to the user indicating that the processing will start
        if not processing_now:
            update.message.reply_text("Please wait. This might take some time!")

        # Enqueue the file for processing
        file_queue.append({"file_name": file_name, "chat_id": chat_id})

        # If not currently processing a file, start processing the queue
        if not processing_now:
            executor.submit(process_file, file_queue.pop(0), context)
            processing_now = True  # Set the flag to indicate that processing is now in progress

    except Exception as e:
        context.bot.send_message(chat_id, f"Error during file processing: {e}")
        print(f"Error during file processing: {e}")

    finally:
        # Check for new files in the queue
        process_file_queue(context)

def handle_text(update: Update, context: CallbackContext) -> None:
    global processing_now
    chat_id = update.message.chat_id
    domain = update.message.text.strip().lower()
    user_id = update.message.from_user.id

    if user_id not in ALLOWED_USER_IDS:
        context.bot.send_message(
            chat_id, "You are not authorized to use this bot.")
        return

    # Generate a unique filename based on the domain
    unique_filename = f"{domain.replace('.', '_')}.txt"
    upload_file_path = os.path.join(UPLOADS_DIR, unique_filename)

    try:
        # Write the domain to a temporary file
        with open(upload_file_path, 'w') as temp_file:
            temp_file.write(domain)

        # Send a message to the user indicating that the processing will start
        if not processing_now:
            update.message.reply_text("Please wait. This might take some time!")

        # Enqueue the file for processing
        file_queue.append({"file_name": unique_filename, "chat_id": chat_id})

        # If not currently processing a file, start processing the queue
        if not processing_now:
            executor.submit(process_file, file_queue.pop(0), context)
            processing_now = True  # Set the flag to indicate that processing is now in progress

    except Exception as e:
        context.bot.send_message(chat_id, f"Error during file processing: {e}")
        print(f"Error during file processing: {e}")

    finally:
        # Check for new files in the queue
        process_file_queue(context)

def main() -> None:
    global executor
    with ThreadPoolExecutor(max_workers=2) as executor:
        updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher

        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(MessageHandler(Filters.document, handle_document))
        dispatcher.add_handler(
            MessageHandler(Filters.text & ~Filters.command, handle_text))

        updater.start_polling()
        updater.idle()

if __name__ == '__main__':
    main()
