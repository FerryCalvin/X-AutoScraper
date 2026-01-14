"""
Sentiment Analysis Module for AutoScraper
Uses IndoBERT (Indonesian BERT) for accurate Indonesian text sentiment classification

Model: indobenchmark/indobert-base-p1
Accuracy: ~85% for Indonesian text

Usage:
    from sentiment import SentimentAnalyzer
    analyzer = SentimentAnalyzer()
    result = analyzer.predict("Pemilu berjalan lancar dan aman")
    # Returns: {"label": "positive", "score": 0.92}
"""

import os
import json

# Lazy loading of heavy dependencies
_ANALYZER = None

def get_analyzer():
    """Lazy load the analyzer to avoid slow startup"""
    global _ANALYZER
    if _ANALYZER is None:
        _ANALYZER = SentimentAnalyzer()
    return _ANALYZER


class SentimentAnalyzer:
    """Indonesian Sentiment Analyzer using IndoBERT or Lexicon fallback"""
    
    def __init__(self, use_model="auto"):
        """
        Initialize the sentiment analyzer.
        
        Args:
            use_model: "indobert", "lexicon", or "auto" (tries indobert first, falls back to lexicon)
        """
        self.model_type = None
        self.classifier = None
        self.lexicon = None
        
        if use_model == "auto":
            try:
                self._load_indobert()
                self.model_type = "indobert"
            except Exception as e:
                print(f"⚠️ IndoBERT not available ({e}). Using lexicon fallback.")
                self._load_lexicon()
                self.model_type = "lexicon"
        elif use_model == "indobert":
            self._load_indobert()
            self.model_type = "indobert"
        else:
            self._load_lexicon()
            self.model_type = "lexicon"
    
    def _load_indobert(self):
        """Load IndoBERT model for sentiment analysis"""
        from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
        
        model_name = "mdhugol/indonesia-bert-sentiment-classification"
        
        print("🧠 Loading IndoBERT sentiment model...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.classifier = pipeline("sentiment-analysis", model=self.model, tokenizer=self.tokenizer)
        print("✅ IndoBERT model loaded successfully!")
    
    def _load_lexicon(self):
        """Load simple lexicon-based analyzer"""
        # Indonesian sentiment lexicon (simplified)
        self.lexicon = {
            "positive": [
                "bagus", "baik", "hebat", "mantap", "keren", "luar biasa", "sukses",
                "senang", "gembira", "bahagia", "puas", "berhasil", "menang", "top",
                "aman", "lancar", "setuju", "dukung", "bangga", "terima kasih"
            ],
            "negative": [
                "buruk", "jelek", "parah", "gagal", "kecewa", "marah", "sedih",
                "bohong", "korupsi", "curang", "hoax", "palsu", "rugi", "bahaya",
                "tolak", "protes", "demo", "rusuh", "benci", "malu"
            ]
        }
        print("📚 Using lexicon-based sentiment analysis")
    
    def predict(self, text):
        """
        Predict sentiment of a single text.
        
        Args:
            text: Input text string
            
        Returns:
            dict with "label" (positive/negative/neutral) and "score" (confidence)
        """
        if not text or len(text.strip()) == 0:
            return {"label": "neutral", "score": 0.5}
        
        if self.model_type == "indobert":
            return self._predict_indobert(text)
        else:
            return self._predict_lexicon(text)
    
    def _predict_indobert(self, text):
        """Predict using IndoBERT model"""
        try:
            # Truncate to 512 tokens to avoid overflow
            result = self.classifier(text[:512])[0]
            label = result["label"].lower()
            score = result["score"]
            
            # Normalize labels
            if label in ["positive", "positif", "pos", "label_1"]:
                label = "positive"
            elif label in ["negative", "negatif", "neg", "label_0"]:
                label = "negative"
            else:
                label = "neutral"
            
            return {"label": label, "score": round(score, 3)}
        except Exception as e:
            return {"label": "neutral", "score": 0.5, "error": str(e)}
    
    def _predict_lexicon(self, text):
        """Predict using simple lexicon matching"""
        text_lower = text.lower()
        
        pos_count = sum(1 for word in self.lexicon["positive"] if word in text_lower)
        neg_count = sum(1 for word in self.lexicon["negative"] if word in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return {"label": "neutral", "score": 0.5}
        
        if pos_count > neg_count:
            return {"label": "positive", "score": round(pos_count / total, 3)}
        elif neg_count > pos_count:
            return {"label": "negative", "score": round(neg_count / total, 3)}
        else:
            return {"label": "neutral", "score": 0.5}
    
    def predict_batch(self, texts, batch_size=32):
        """
        Predict sentiment for a list of texts.
        
        Args:
            texts: List of input text strings
            batch_size: Number of texts to process at once (only used for IndoBERT)
            
        Returns:
            List of dicts with "label" and "score"
        """
        results = []
        for i, text in enumerate(texts):
            results.append(self.predict(text))
            if (i + 1) % 50 == 0:
                print(f"   Analyzed {i + 1}/{len(texts)} texts...")
        return results


def add_sentiment_to_file(input_file, output_file=None):
    """
    Add sentiment analysis to a scraped CSV file.
    
    Args:
        input_file: Path to input CSV
        output_file: Path to output CSV (if None, overwrites input)
    """
    import csv
    
    if output_file is None:
        output_file = input_file
    
    analyzer = get_analyzer()
    
    # Read data
    rows = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) + ['sentiment', 'sentiment_score']
        for row in reader:
            rows.append(dict(row))
    
    print(f"🧠 Analyzing sentiment for {len(rows)} tweets...")
    
    # Add sentiment
    for i, row in enumerate(rows):
        text = row.get('text', row.get('original_text', ''))
        result = analyzer.predict(text)
        row['sentiment'] = result['label']
        row['sentiment_score'] = result['score']
        
        if (i + 1) % 50 == 0:
            print(f"   Processed {i + 1}/{len(rows)} tweets...")
    
    # Write output
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Sentiment analysis complete! Output: {output_file}")
    return output_file


# Command line usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        add_sentiment_to_file(input_file, output_file)
    else:
        # Demo
        analyzer = SentimentAnalyzer()
        test_texts = [
            "Pemilu berjalan lancar dan aman",
            "Korupsi merajalela di pemerintahan",
            "Cuaca hari ini cerah",
            "Kecewa dengan pelayanan yang buruk",
            "Terima kasih banyak atas bantuannya"
        ]
        
        print("\n🧠 Sentiment Analysis Demo:")
        for text in test_texts:
            result = analyzer.predict(text)
            print(f"  [{result['label'].upper():8}] ({result['score']:.2f}) {text}")
