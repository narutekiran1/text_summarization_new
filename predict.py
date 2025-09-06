import numpy as np
import pandas as pd
import nltk
import re
from nltk.corpus import stopwords
from nltk.tokenize.punkt import PunktSentenceTokenizer
from gensim.models import Word2Vec
from scipy.spatial import distance
import networkx as nx

# Ensure 'punkt' and 'stopwords' are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')


def summarize(filepath=None, paragraph=''):
    tokenizer = PunktSentenceTokenizer()

    # Read text from file if filepath is provided
    if filepath:
        with open(filepath, "r", encoding="utf8") as f:
            text = f.read()
        Broken_in_sentences = tokenizer.tokenize(text)
    else:
        Broken_in_sentences = tokenizer.tokenize(paragraph)

    # If no valid sentences, return empty
    if not Broken_in_sentences:
        return ["No sentences available for summarization."]

    # Clean sentences (remove punctuation and convert to lowercase)
    Broken_in_sentences_clean = [re.sub(r'[^\w\s]', '', sentence.lower()) for sentence in Broken_in_sentences]

    # Load English stopwords
    Unnecessary_words = set(stopwords.words('english'))

    # Tokenize and remove stopwords
    Tokenized_sentence = [[word for word in sentence.split() if word not in Unnecessary_words] for sentence in Broken_in_sentences_clean]

    # Ensure at least one word per sentence
    Tokenized_sentence = [sentence for sentence in Tokenized_sentence if sentence]

    # If no valid words, return original text
    if not Tokenized_sentence:
        return ["No valid words found after tokenization."]

    # Train Word2Vec model
    w2v = Word2Vec(sentences=Tokenized_sentence, vector_size=1, min_count=1, epochs=1000)

    # Convert sentences to vectors
    sentence_embedded_value = [
        [w2v.wv[word][0] for word in words if word in w2v.wv]
        for words in Tokenized_sentence
    ]

    # Handle empty sentences
    max_len = max((len(tokens) for tokens in Tokenized_sentence), default=1)
    sentence_embedded_value = [
        np.pad(embedding, (0, max_len - len(embedding)), 'constant') if embedding else np.zeros(max_len)
        for embedding in sentence_embedded_value
    ]

    # Create similarity matrixs
    similarity_matrix = np.zeros([len(Tokenized_sentence), len(Tokenized_sentence)])
    for i, row_embedding in enumerate(sentence_embedded_value):
        for j, column_embedding in enumerate(sentence_embedded_value):
            similarity_matrix[i][j] = 1 - distance.cosine(row_embedding, column_embedding) if np.any(row_embedding) and np.any(column_embedding) else 0

    # Add small smoothing value to avoid disconnected graph
    eps = 1e-6
    similarity_matrix += eps

    # Convert to graph
    nx_graph = nx.from_numpy_array(similarity_matrix)

    try:
        scores = nx.pagerank(nx_graph, alpha=0.85, max_iter=1000, tol=1e-6)
    except nx.PowerIterationFailedConvergence:
        print("⚠️ PageRank failed to converge! Using uniform scores.")
        scores = {i: 1/len(Broken_in_sentences) for i in range(len(Broken_in_sentences))}

    # Select top-ranked sentences
    top_sentence = {Broken_in_sentences[index]: scores[index] for index in range(len(Broken_in_sentences))}
    top = dict(sorted(top_sentence.items(), key=lambda x: x[1], reverse=True)[:3])

    # Return summarized sentences
    summarized_text = [sent for sent in Broken_in_sentences if sent in top]
    print(" ".join(summarized_text))
    return summarized_text
