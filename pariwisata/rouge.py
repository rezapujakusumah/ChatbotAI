from rouge_score import rouge_scorer
import pandas as pd
import csv
from datetime import datetime
from pathlib import Path

def load_reference_responses():
    """Load reference responses from CSV file"""
    reference_responses = {}
    with open('data_objek_wisata.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            reference_responses[row['NAMA OBJEK WISATA']] = row['DESKRIPSI OBJEK WISATA']
    return reference_responses

def evaluate_response(generated_response, reference_response):
    """Calculate ROUGE scores for a single response"""
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = scorer.score(reference_response, generated_response)
    return {
        'rouge1': scores['rouge1'].fmeasure,
        'rouge2': scores['rouge2'].fmeasure,
        'rougeL': scores['rougeL'].fmeasure
    }

def save_evaluation_results(results, output_file='rouge_evaluation.csv'):
    """Save evaluation results to CSV file"""
    # Prepare data for CSV
    csv_data = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for result in results:
        row = {
            'timestamp': timestamp,
            'reference_name': result['reference_name'],
            'generated_response': result['generated'],
            'reference_response': result['reference'],
            'rouge1_score': result['scores']['rouge1'],
            'rouge2_score': result['scores']['rouge2'],
            'rougeL_score': result['scores']['rougeL'],
            'average_score': sum(result['scores'].values()) / len(result['scores'])
        }
        csv_data.append(row)
    
    # Convert to DataFrame and save
    df = pd.DataFrame(csv_data)
    
    # Check if file exists to determine if we need to write headers
    file_exists = Path(output_file).exists()
    
    # Save to CSV
    df.to_csv(output_file, 
              mode='a' if file_exists else 'w',
              header=not file_exists,
              index=False,
              encoding='utf-8')
    
    return df

def evaluate_chatbot_responses(chat_history, reference_responses):
    """Evaluate all chatbot responses against references"""
    results = []
    # Tambahkan tracking untuk mencegah duplikasi
    processed_responses = set()
    
    for message in chat_history:
        if message['sender'] == 'bot':
            # Skip jika response sudah pernah diproses
            if message['message'] in processed_responses:
                continue
                
            processed_responses.add(message['message'])
            
            best_score = 0
            best_match = None
            
            for ref_name, ref_text in reference_responses.items():
                scores = evaluate_response(message['message'], ref_text)
                avg_score = sum(scores.values()) / len(scores)
                
                if avg_score > best_score:
                    best_score = avg_score
                    best_match = {
                        'reference_name': ref_name,
                        'generated': message['message'],
                        'reference': ref_text,
                        'scores': scores
                    }
            
            if best_match:
                results.append(best_match)
    
    # Save results to CSV
    save_evaluation_results(results)
    return results

def print_evaluation_results(results):
    """Print evaluation results in a readable format"""
    print("\nROUGE Evaluation Results:")
    print("-" * 80)
    
    avg_scores = {'rouge1': 0, 'rouge2': 0, 'rougeL': 0}
    
    for i, result in enumerate(results, 1):
        print(f"\nResponse {i}:")
        print(f"Reference: {result['reference_name']}")
        print(f"ROUGE-1: {result['scores']['rouge1']:.4f}")
        print(f"ROUGE-2: {result['scores']['rouge2']:.4f}")
        print(f"ROUGE-L: {result['scores']['rougeL']:.4f}")
        
        for metric in avg_scores:
            avg_scores[metric] += result['scores'][metric]
    
    if results:
        print("\nAverage Scores:")
        for metric in avg_scores:
            avg_scores[metric] /= len(results)
            print(f"Average {metric.upper()}: {avg_scores[metric]:.4f}")

def main():
    # Load reference responses
    reference_responses = load_reference_responses()
    
    # Example chat history
    chat_history = [
        {'sender': 'user', 'message': 'Apa itu Cipanas Cileungsing?'},
        {'sender': 'bot', 'message': 'Cipanas Cileungsing adalah pemandian air panas yang terletak di Desa Cilangkap, Kecamatan Buah Bua. Tempat ini populer untuk wisatawan lokal dan memiliki manfaat kesehatan. Selain berendam, pengunjung dapat bersantai di taman yang disediakan.'}
    ]
    
    # Evaluate responses
    results = evaluate_chatbot_responses(chat_history, reference_responses)
    
    # Save results to CSV
    df = save_evaluation_results(results)
    print(f"\nResults saved to rouge_evaluation.csv")
    print("\nLatest evaluation results:")
    print(df.to_string(index=False))

if __name__ == '__main__':
    main()
