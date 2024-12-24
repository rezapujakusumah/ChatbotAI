from flask import Flask, render_template, request, jsonify
import time
import os
import google.generativeai as genai
import googlemaps
from textblob import TextBlob
from datetime import datetime
from googletrans import Translator
import csv
from pathlib import Path
from rouge_score import rouge_scorer
import pandas as pd
from rouge import load_reference_responses, evaluate_response, save_evaluation_results, evaluate_chatbot_responses

app = Flask(__name__)

# Configure Gemini
genai.configure(api_key="AIzaSyB6B3gXF3nTY52DywaaGFyS-FzuBej_96Y")

GOOGLE_MAPS_API_KEY = "AIzaSyClY8LDWvFDQrEgxCZjY2F03CPl3pMuTdI"
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

# Tambahkan translator
translator = Translator()

# Tambahkan konstanta untuk path file CSV
CSV_FILE_PATH = 'reviews_data.csv'

# Tambahkan daftar objek wisata
WISATA_SUMEDANG = [
    {
        'nama': 'Bendungan Jatigede',
        'kategori': 'Bendungan & Danau'
    },
    {
        'nama': 'Gunung Kunci',
        'kategori': 'Wisata Alam'
    },
    {
        'nama': 'Taman Endog',
        'kategori': 'Taman Rekreasi'
    },
    {
        'nama': 'Situ Cipanten',
        'kategori': 'Bendungan & Danau'
    },
    {
        'nama': 'Curug Cigorobog',
        'kategori': 'Air Terjun'
    },
    {
        'nama': 'Alun-alun Sumedang',
        'kategori': 'Taman Kota'
    }
]

# Fungsi untuk memeriksa dan membuat file CSV jika belum ada
def initialize_csv():
    if not Path(CSV_FILE_PATH).exists():
        with open(CSV_FILE_PATH, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Tanggal', 'Lokasi', 'Rating', 'Review', 'Sentimen', 'Skor Sentimen'])

# Fungsi untuk menyimpan review ke CSV
def save_review_to_csv(review_data):
    with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            review_data['date'],
            review_data['location'],
            review_data['rating'],
            review_data['text'],
            review_data['sentiment'],
            review_data['sentiment_score']
        ])

# Fungsi untuk membaca semua review dari CSV
def read_reviews_from_csv():
    reviews = []
    if Path(CSV_FILE_PATH).exists():
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                reviews.append({
                    'date': row['Tanggal'],
                    'location': row['Lokasi'],
                    'rating': row['Rating'],
                    'text': row['Review'],
                    'sentiment': row['Sentimen'],
                    'sentiment_score': float(row['Skor Sentimen'])
                })
    return reviews

# Initialize files and chat session globally
def initialize_gemini():
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    files = [
        upload_to_gemini("data_objek_wisata.csv", mime_type="text/csv"), 
    ]
    files2 = [
        upload_to_gemini("budaya_sunda.pdf", mime_type="application/pdf"),
    ]
    files3 = [
        upload_to_gemini("sejarah.pdf", mime_type="application/pdf"),
    ]
    files4 = [
        upload_to_gemini("data_hotel.csv", mime_type="text/csv"),
    ]

    wait_for_files_active(files)
    
    # Add initial prompt about Sumedang tourism FAQ
    initial_prompt = """
    Sumedang adalah salah satu Kabupaten di Jawa Barat. Beberapa pertanyaan umum terkait Pariwisata Sumedang sering muncul dari wisatawan yang ingin mengunjungi Sumedang.

    Pertanyaan yang sering ditanyakan:
    1. Kapan waktu terbaik untuk mengunjungi Sumedang?
    2. Apakah ada objek wisata di Sumedang destinasi yang ramah anak?
    3. Bagaimana cara ke sumedang atau ke destinasi wisata
    4. Apa saja wisata terbaik yang ada di sumedang
    5. Berikan rekomendasi Oleh-oleh khas sumedang
    6. Apakah ada transportasi umum untuk ke tempat wisata?
    7. Jadwal Event yang ada di Sumedang
    8. Berapa harga tiket objek wisata Jans Park Jatinangor?
    9. Berikan rekomendasi Hotel yang dekat dengan tempat wisata
    10. Berikan Rekomendasi destinasi kuliner terkenal dan enak

    Jawaban potensial:
    1. Dibulan April-Mei di Hari jadi Kabupaten Sumedang karena banyak event yang diselenggarakan
    2. Bisa ke Museum Prabu Geusan Ulun untuk belajar sejarah Sumedang atau Janspark Di Jatinangor bisa jadi pilihan banyak wahana permainan
    3. Cara jika ingin mengunjungi Sumedang ada beberapa opsi seperti menggunakan Travel atau bus jika anda dari luar kota bisa juga menggunakan Tol CISUMDAWU jika menggunakan mobil pribadi, menggunakan angkot jika berada di daerah Bandung Raya
    4. Ada beberapa wisata terbaik di Sumedang, anda bisa mengunjungi Jans Park Jatinangor, Menara kujang sapasang Jatigede, Tanjung duriat, dan Mesjid Al-Kamil Jatigede 
    5. Anda bisa memilih Tahu Sumedang, opak, mangga gedong gincu, atau ubi cilembu
    6. Anda bisa menggunakan ojek online atau angkot. Untuk angkot bisa menggunakan angkot nomor 04 berwarna coklat
    7. Anda dapat mengakses jadwal event di Sumedang melalui halaman web: disparbudpora.kabsmd.go.id atau melalui media sosial Disparbudpora Kab Sumedang instagram: @disparbudporakabsumedang.
    8. Untuk harga masuk pada weekday Rp. 30.000 untuk weekend Rp. 40.000 
    9. Anda bisa mencoba menginap di Hotel Puri Khatulistiwa karena dengan dengan tempat wisata Janspark hanya berjarak sejauh 2 Km
    10. Untuk Kuliner anda dapat mencoba Tahu Bungkeng sebagai pelopor penjual tahu pertama atau untuk segar es krim idola, anda juga bisa mencoba mengunjungi restoran warung pengkolan jati yang menyediakan menu utama yaitu ayam bakakak 


    Gunakan jawaban potensial untuk menjawab pertanyaan-pertanyaan tersebut, berikan jawaban dengan konsisten mengikuti jawaban potensial. Jika ada pertanyaan yang tidak bisa dijawab, alihkan ke admin.

    HAL YANG PERLU DIINGAT:
    1. Jika ada pertanyaan terkait rekomendasi objek wisata berikan jawaban berdasarkan data kunjungan paling banyak dikunjungi
    2. Jika ada pertanyaan terkait rekomendasi objek wisata berikan hanya 5 saja berdasarkan data kunjungan paling banyak dikunjungi

    """
    
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                    files[0], files2[0], files3[0], files4[0],
                    initial_prompt
                ],
            },
        ]
    )
    
    return chat_session

# Your existing helper functions
def upload_to_gemini(path, mime_type=None):
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def wait_for_files_active(files):
    print("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    print("...all files ready")
    print()

# Initialize chat session
chat_session = initialize_gemini()

# Tambahkan struktur data untuk menyimpan review (idealnya gunakan database)
reviews = []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data['message']
    chat_history = data.get('history', [])  # Get chat history if available
    
    if user_message.lower() == 'quit':
        return jsonify({'response': 'Goodbye!'})
    
    # Add chat history context to the message
    context = "\n".join([
        f"{msg['sender']}: {msg['message']}" 
        for msg in chat_history[-5:]  # Use last 5 messages for context
    ])
    
    # Send message with context to Gemini
    response = chat_session.send_message(f"Previous context:\n{context}\n\nUser: {user_message}")
    
    # Format response
    lines = response.text.split('\n')
    formatted_lines = []
    counter = 1
    
    # Process each line
    for line in lines:
        # If line starts with bullet point or dash, replace with number
        if line.strip().startswith(('•', '-', '*')):
            line = f"{counter}. {line.strip()[1:].strip()}"
            counter += 1
        formatted_lines.append(line)
    
    # Join lines back together with HTML line breaks
    formatted_response = "<br>".join(formatted_lines)
    formatted_response = formatted_response.replace("**", "")
    
    # Evaluasi response
    reference_responses = load_reference_responses()
    chat_history = [
        {'sender': 'user', 'message': request.json['message']},
        {'sender': 'bot', 'message': formatted_response}
    ]
    
    # Evaluate dan save ke CSV
    results = evaluate_chatbot_responses(chat_history, reference_responses)
    save_evaluation_results(results)
    
    return jsonify({
        'response': formatted_response,
        'evaluation_results': results[0] if results else None
    })

@app.route('/review', methods=['GET'])
def review_page():
    return render_template('review.html', wisata_list=WISATA_SUMEDANG)

@app.route('/submit-review', methods=['POST'])
def submit_review():
    data = request.json
    review_text = data['review']
    location = data['location']
    rating = data['rating']
    
    try:
        # Terjemahkan teks review ke bahasa Inggris
        translated = translator.translate(review_text, src='id', dest='en')
        english_text = translated.text
        
        # Analisis sentimen menggunakan teks bahasa Inggris
        analysis = TextBlob(english_text)
        sentiment_score = analysis.sentiment.polarity
        
        # Sesuaikan threshold untuk kategorisasi sentimen
        if sentiment_score > 0.1:
            sentiment = "positif"
        elif sentiment_score < -0.1:
            sentiment = "negatif"
        else:
            sentiment = "netral"
        
        # Buat data review
        review_data = {
            'text': review_text,
            'location': location,
            'rating': rating,
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Simpan ke CSV
        save_review_to_csv(review_data)
        
        # Simpan ke list di memory
        reviews.append(review_data)
        
        return jsonify({
            'status': 'success',
            'sentiment': sentiment,
            'sentiment_score': round(sentiment_score, 2)
        })
        
    except Exception as e:
        print(f"Error in sentiment analysis: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Terjadi kesalahan dalam analisis sentimen'
        }), 500

@app.route('/get-reviews', methods=['GET'])
def get_reviews():
    reviews = read_reviews_from_csv()
    return jsonify(reviews)

if __name__ == '__main__':
    initialize_csv()
    app.run(debug=True)