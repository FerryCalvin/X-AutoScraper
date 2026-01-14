"""
Topic Modeling Module for AutoScraper
Uses LDA (Latent Dirichlet Allocation) for topic extraction from tweets

Usage:
    from topic_model import TopicModeler
    modeler = TopicModeler()
    topics = modeler.extract_topics(texts, num_topics=5)
"""

import re
from collections import Counter

# Lazy loading
_MODELER = None

def get_modeler():
    global _MODELER
    if _MODELER is None:
        _MODELER = TopicModeler()
    return _MODELER


class TopicModeler:
    """Simple Topic Modeler using TF-IDF + LDA or word frequency fallback"""
    
    def __init__(self, use_sklearn=True):
        self.use_sklearn = use_sklearn
        self.vectorizer = None
        self.lda_model = None
        
        # Indonesian stopwords (common words to ignore)
        self.stopwords = set([
            "dan", "yang", "di", "ke", "dari", "ini", "itu", "untuk", "dengan",
            "pada", "adalah", "atau", "juga", "akan", "ada", "saya", "kamu", 
            "kami", "mereka", "dia", "anda", "nya", "ya", "tidak", "bisa",
            "sudah", "belum", "harus", "dalam", "oleh", "sebagai", "seperti",
            "jika", "maka", "agar", "tapi", "karena", "sehingga", "namun",
            "lagi", "masih", "lebih", "sangat", "sekali", "paling", "saat",
            "setelah", "sebelum", "antara", "hingga", "sampai", "tanpa",
            "bukan", "hanya", "saja", "cuma", "pun", "kah", "lah", "dong"
        ])
        
        if use_sklearn:
            try:
                self._init_sklearn()
            except ImportError:
                print("⚠️ sklearn not available. Using simple word frequency.")
                self.use_sklearn = False
    
    def _init_sklearn(self):
        """Initialize sklearn components"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import LatentDirichletAllocation
        
        self.TfidfVectorizer = TfidfVectorizer
        self.LDA = LatentDirichletAllocation
    
    def preprocess(self, text):
        """Clean and tokenize text"""
        if not text:
            return []
        
        # Lowercase
        text = text.lower()
        
        # Remove URLs, mentions, hashtags for topic analysis
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#\w+', '', text)
        
        # Remove non-alphanumeric (keep Indonesian characters)
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Tokenize
        words = text.split()
        
        # Remove stopwords and short words
        words = [w for w in words if w not in self.stopwords and len(w) > 2]
        
        return words
    
    def extract_topics(self, texts, num_topics=5, words_per_topic=10):
        """
        Extract main topics from a list of texts.
        
        Args:
            texts: List of text strings
            num_topics: Number of topics to extract
            words_per_topic: Number of words per topic
            
        Returns:
            List of topic dicts with "id", "words", and "weight"
        """
        if not texts:
            return []
        
        if self.use_sklearn:
            return self._extract_sklearn(texts, num_topics, words_per_topic)
        else:
            return self._extract_simple(texts, num_topics, words_per_topic)
    
    def _extract_sklearn(self, texts, num_topics, words_per_topic):
        """Extract topics using LDA"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import LatentDirichletAllocation
        
        # Preprocess all texts
        processed = [' '.join(self.preprocess(t)) for t in texts]
        
        # Filter out empty texts
        processed = [t for t in processed if len(t) > 0]
        
        if len(processed) < num_topics:
            print(f"⚠️ Not enough data for {num_topics} topics. Falling back to simple method.")
            return self._extract_simple(texts, num_topics, words_per_topic)
        
        # TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=1000,
            min_df=2,
            max_df=0.95
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform(processed)
        except ValueError as e:
            print(f"⚠️ TF-IDF error: {e}. Falling back to simple method.")
            return self._extract_simple(texts, num_topics, words_per_topic)
        
        # LDA
        lda = LatentDirichletAllocation(
            n_components=num_topics,
            random_state=42,
            max_iter=10
        )
        lda.fit(tfidf_matrix)
        
        # Extract topics
        feature_names = vectorizer.get_feature_names_out()
        topics = []
        
        for idx, topic in enumerate(lda.components_):
            top_word_indices = topic.argsort()[:-words_per_topic-1:-1]
            top_words = [feature_names[i] for i in top_word_indices]
            weight = float(topic[top_word_indices].sum())
            
            topics.append({
                "id": idx + 1,
                "words": top_words,
                "weight": round(weight, 2)
            })
        
        return topics
    
    def _extract_simple(self, texts, num_topics, words_per_topic):
        """Simple word frequency-based topic extraction"""
        all_words = []
        for text in texts:
            words = self.preprocess(text)
            all_words.extend(words)
        
        # Count frequencies
        word_counts = Counter(all_words)
        
        # Get top words
        top_words = [word for word, count in word_counts.most_common(num_topics * words_per_topic)]
        
        # Group into "topics" (somewhat arbitrary grouping)
        topics = []
        for i in range(num_topics):
            start = i * words_per_topic
            end = start + words_per_topic
            topic_words = top_words[start:end]
            
            if topic_words:
                topics.append({
                    "id": i + 1,
                    "words": topic_words,
                    "weight": len(topic_words) / words_per_topic
                })
        
        return topics


def analyze_topics_from_file(input_file, num_topics=5, words_per_topic=10):
    """
    Extract topics from a scraped CSV file.
    
    Args:
        input_file: Path to input CSV
        num_topics: Number of topics to extract
        words_per_topic: Number of words per topic
        
    Returns:
        List of topic dicts
    """
    import csv
    
    modeler = get_modeler()
    
    # Read texts
    texts = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get('text', row.get('original_text', ''))
            if text:
                texts.append(text)
    
    print(f"📊 Extracting {num_topics} topics from {len(texts)} tweets...")
    
    topics = modeler.extract_topics(texts, num_topics, words_per_topic)
    
    print("\n📌 Detected Topics:")
    for topic in topics:
        print(f"   Topic {topic['id']}: {', '.join(topic['words'][:5])}...")
    
    return topics


# Command line usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        num_topics = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        analyze_topics_from_file(input_file, num_topics)
    else:
        # Demo
        test_texts = [
            "Pemilu 2024 berjalan lancar dan aman di seluruh Indonesia",
            "Prabowo dan Gibran menang telak dalam pemilihan presiden",
            "Anies dan Imin melakukan kampanye di Jawa Barat",
            "KPU mengumumkan hasil rekapitulasi suara nasional",
            "Ganjar mendapat dukungan dari partai PDIP",
            "Debat capres berlangsung seru dan informatif",
            "Ekonomi Indonesia bertumbuh positif tahun ini",
            "Rupiah menguat terhadap dollar AS",
            "Banjir melanda Jakarta akibat hujan deras",
            "BMKG mengeluarkan peringatan cuaca buruk"
        ]
        
        modeler = TopicModeler()
        topics = modeler.extract_topics(test_texts, num_topics=3, words_per_topic=5)
        
        print("\n📊 Topic Modeling Demo:")
        for topic in topics:
            print(f"  Topic {topic['id']}: {', '.join(topic['words'])}")
