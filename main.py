import os
import sys
import PyPDF2
import re
from openai import OpenAI
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import json

# Load the OpenAI client using the correct pattern
def load_openai_client():
    api_key = load_openai_key()
    client = OpenAI(api_key=api_key)
    return client

# Function to read API key from key.txt
def load_openai_key():
    try:
        with open("key.txt", "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        print("Error: 'key.txt' file not found. Please create a key.txt file with your OpenAI API key.")
        sys.exit()

# Function to select a PDF file using a file dialog
def select_pdf_file():
    Tk().withdraw()  # Hide the root window
    file_path = askopenfilename(filetypes=[("PDF files", "*.pdf")], title="Select a PDF file")
    if not file_path:
        print("No file selected. Exiting.")
        sys.exit()
    return file_path

# Extract text from each page of the PDF
def extract_text_from_pdf(pdf_path):
    text_pages = []
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text:
                    text_pages.append((page_num + 1, text))
            except Exception as e:
                print(f"Error reading page {page_num + 1}: {e}")
    return text_pages

# Updated function to check relevance using OpenAI
def is_relevant_text(client, text):
    prompt = f"""
Analyze the following text and determine if it contains relevant, substantive content for creating flashcards. 
Ignore table of contents, indexes, appendices, or pages with minimal text.
Respond with only "YES" if the content is relevant, or "NO" if it's not.

Text to analyze:
\"\"\"{text[:1000]}\"\"\"  # Limit to first 1000 characters to save tokens
"""
    
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant that determines text relevance."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1  # We only need a short response
    )

    response = completion.choices[0].message.content.strip().upper()
    return response == "YES"

# Function to generate Anki cards using the OpenAI Chat API
def generate_anki_cards(client, text):
    prompt = f"""
You are an assistant that creates Anki flashcards to help memorize the content.

Please generate 3 to 8 high-quality Anki flashcards based on the following text:

\"\"\"{text}\"\"\"

Ensure that the cards cover key concepts and important details. The cards should be concise and clear. Please respond using JSON with the following format:

{{
    "cards": [
        {{
            "front": "Front of the card",
            "back": "Back of the card"
        }}
    ]
}}
"""
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant that creates Anki flashcards."},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" }
    )

    cards_json = completion.choices[0].message.content.strip()
    cards = []
    try:
        cards_data = json.loads(cards_json)
        for card in cards_data.get("cards", []):
            front = card.get("front")
            back = card.get("back")
            if front and back:
                cards.append(f"{front};{back}")
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON response from OpenAI.")
        return []
    return cards

# Function to save the generated Anki cards to a text file
def save_cards_to_file(cards, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        for card in cards:
            f.write(card + '\n')
    print(f"Anki cards have been saved to {output_file}")

# Main function to drive the process
def main():
    # Load OpenAI client
    client = load_openai_client()

    # Select the PDF file
    pdf_path = select_pdf_file()

    # Extract text from PDF pages
    pages = extract_text_from_pdf(pdf_path)
    all_cards = []

    # Process each page, generate Anki cards for relevant content
    for page_num, text in pages:
        print(f"Checking relevance of page {page_num}...")
        if is_relevant_text(client, text):
            print(f"Processing page {page_num}...")
            cards = generate_anki_cards(client, text)
            all_cards.extend(cards)
        else:
            print(f"Skipping page {page_num} as it seems irrelevant.")

    # Save cards to a file
    if all_cards:
        output_file = os.path.splitext(pdf_path)[0] + '_anki_cards.txt'
        save_cards_to_file(all_cards, output_file)
    else:
        print("No relevant content found to generate Anki cards.")

if __name__ == "__main__":
    main()
