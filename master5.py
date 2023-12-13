import asyncio
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from telegram import Bot

url_pattern = r'(?!https?://)([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'

def generate_previous_file_path():
    current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    return f'previous_domains_{current_datetime}.txt'

def load_previous_domains(file_path):
    try:
        with open(file_path, 'r') as previous_file:
            return set(line.strip() for line in previous_file)
    except FileNotFoundError:
        return set()

def update_previous_domains(file_path, new_domains):
    with open(file_path, 'a') as previous_file:
        for domain in new_domains:
            previous_file.write(domain + '\n')

def extract_and_store_unique_three_part_urls_exclude(input_file_path, output_file_path, blacklist_file_path, previous_file_path):
    try:
        unique_urls = set()
        previous_domains = load_previous_domains(previous_file_path)

        with open(blacklist_file_path, 'r') as blacklist_file:
            blacklist_words = set(line.strip() for line in blacklist_file)

        with open(input_file_path, 'r') as input_file, open(output_file_path, 'w') as output_file:
            lines = input_file.readlines()
            total_lines = len(lines)
            if total_lines == 0:
                print("Input file is empty.")
                return

            for line_num, line in enumerate(lines, start=1):
                urls = re.findall(url_pattern, line)
                if urls:
                    for url in urls:
                        if not any(url.endswith(exclusion) for exclusion in blacklist_words) and url not in unique_urls and url not in previous_domains:
                            unique_urls.add(url)
                            output_file.write(url + '\n')

            print("\nProcessing complete.")
            update_previous_domains(previous_file_path, unique_urls)
    except FileNotFoundError:
        print(f"Input file, blacklist file, or previous file not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def extract_urls_from_webpage(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        return [link['href'] for link in links]
    except Exception as e:
        print(f"An error occurred while extracting URLs from the webpage: {str(e)}")
        return []

def format_time_remaining(seconds):
    return str(timedelta(seconds=seconds))

async def send_to_telegram(bot_token, chat_id, file_path, remaining_time):
    bot = Bot(token=bot_token)
    try:
        with open(file_path, 'rb') as file:
            caption = f"Filtered URLs sent to Telegram. Waiting for {format_time_remaining(remaining_time)} before the next execution..."
            await bot.send_document(chat_id=chat_id, document=file, caption=caption)
    except Exception as e:
        print(f"An error occurred while sending the file to Telegram: {str(e)}")

async def main():
    bot_token = '6828435487:AAFfzO-B-IU-QF7X5EEQEDDkdUX0r9S08Ck'
    chat_ids = ['1187810967']  # Add all the chat IDs you want to send messages to

    webpage_url = 'https://subdomainfinder.c99.nl/overview'
    # webpage_url = 'https://atsameip.intercode.ca/'
    blacklist_file_path = 'blacklist.txt'
    waiting_value = 1 * 60  # Set the initial waiting time in seconds

    while True:
        previous_file_path = generate_previous_file_path()
        final_output_path = f'filtered_urls_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.txt'

        extracted_urls = extract_urls_from_webpage(webpage_url)
        with open('temp_urls.txt', 'w') as temp_output_file:
            for url in extracted_urls:
                temp_output_file.write(url + '\n')

        extract_and_store_unique_three_part_urls_exclude('temp_urls.txt', final_output_path, blacklist_file_path, previous_file_path)

        for chat_id in chat_ids:
            await send_to_telegram(bot_token, chat_id, final_output_path, waiting_value)

        print(f"Script executed successfully. Filtered URLs sent to Telegram. Waiting for {format_time_remaining(waiting_value)} before the next execution...", end='\r')

        for remaining_time in range(waiting_value, 0, -1):
            await asyncio.sleep(1)  # Use asyncio.sleep for asynchronous sleep
            print(f"Waiting for {format_time_remaining(remaining_time)} before the next execution...", end='\r')

if __name__ == "__main__":
    asyncio.run(main())  # Use asyncio.run to run the asynchronous main function