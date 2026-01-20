#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding Utilities - Shared embedding infrastructure for Relation-ship tools
==============================================================================

# Kali [Visionary]: This module consolidates embedding code. GPU power, unified.
#
# Athena [Reviewer]: All tools use all-MiniLM-L6-v2 (384 dimensions).
#     This module standardizes the pipeline: load -> encode -> similarity.
#
# Vesta [Architect]: Handles CUDA detection, batch encoding, and
#     both single-pair and batch cosine similarity.
#
# Nemesis [Security]: No external API calls. All local computation.
#     Embeddings never leave the machine.
#
# Klea [Product]: ...the same understanding, computed the same way.

MIRA-OSS Integration:
    This is Phase 1 of the MIRA-inspired tool unification.
    Unified embeddings enable unified indices (Phase 2).

Attribution:
    MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS, AGPL)
    Original Paradoxa implementation by Nathan Batty & Paradoxa (Human-AI Collaboration)

Usage:
    from embedding_utils import load_model, encode_texts, cosine_similarity

    model = load_model()
    embeddings = encode_texts(texts, model)
    sim = cosine_similarity(emb1, emb2)
"""

import sys
from pathlib import Path
from typing import List, Optional, Union

# Handle imports whether run as module or script
_tools_dir = Path(__file__).parent
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from shared_config import (
    Colors,
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    check_embedding_dependencies,
)

# =============================================================================
# OPTIONAL NUMPY IMPORT
# =============================================================================
# Kali [Visionary]: Numpy is optional but needed for embeddings
# Athena [Documentation]: Import at top if available, None if not

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


# =============================================================================
# MODEL LOADING
# =============================================================================
# Kali [Visionary]: GPU if available, CPU if not
# Athena [Reviewer]: Caches model to avoid repeated loading
# Vesta [Builder]: Returns None if dependencies missing

_cached_model = None
_cached_model_name = None


def load_model(model_name: str = DEFAULT_EMBEDDING_MODEL,
               device: str = 'auto',
               verbose: bool = True) -> Optional[object]:
    """
    Load the embedding model with GPU support if available.

    # Kali [Visionary]: One model, shared across all tools
    # Athena [Documentation]: Returns None if deps missing
    # Vesta [DevOps]: Caches model to avoid repeated loading

    Args:
        model_name: Model identifier (default: all-MiniLM-L6-v2)
        device: 'auto', 'cuda', or 'cpu'
        verbose: Whether to print loading messages

    Returns:
        Loaded SentenceTransformer model, or None if deps missing
    """
    global _cached_model, _cached_model_name

    # Return cached model if same name requested
    if _cached_model is not None and _cached_model_name == model_name:
        return _cached_model

    if not check_embedding_dependencies(verbose=verbose):
        return None

    from sentence_transformers import SentenceTransformer
    import torch

    if verbose:
        print(f"{Colors.CYAN}Loading embedding model: {model_name}{Colors.END}")

    model = SentenceTransformer(model_name, trust_remote_code=True)

    # Determine device
    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    if verbose:
        print(f"  Device: {Colors.GREEN}{device}{Colors.END}")
        if device == 'cuda':
            print(f"  GPU: {Colors.GREEN}{torch.cuda.get_device_name(0)}{Colors.END}")

    model = model.to(device)

    # Cache for reuse
    _cached_model = model
    _cached_model_name = model_name

    return model


def get_device() -> str:
    """
    Get the best available device (cuda or cpu).

    # Vesta [DevOps]: Quick check without loading model
    """
    try:
        import torch
        return 'cuda' if torch.cuda.is_available() else 'cpu'
    except ImportError:
        return 'cpu'


# =============================================================================
# TEXT ENCODING
# =============================================================================
# Kali [Visionary]: Transform text to meaning-vectors
# Athena [Reviewer]: Handles batching, progress bars, numpy output


def encode_texts(texts: List[str],
                 model: Optional[object] = None,
                 batch_size: int = 32,
                 show_progress: bool = True,
                 normalize: bool = True) -> Optional['np.ndarray']:
    """
    Encode texts to embeddings using the model.

    # Kali [Visionary]: Text -> semantic vectors
    # Athena [Documentation]: Returns (n, 384) numpy array
    # Vesta [Builder]: Handles batching internally

    Args:
        texts: List of strings to encode
        model: Pre-loaded model (loads default if None)
        batch_size: Encoding batch size
        show_progress: Whether to show progress bar
        normalize: Whether to L2-normalize embeddings

    Returns:
        Numpy array of shape (n, embedding_dim), or None if error
    """
    if not HAS_NUMPY:
        print(f"{Colors.YELLOW}numpy not installed{Colors.END}")
        return None

    if not texts:
        return np.array([])

    if model is None:
        model = load_model(verbose=False)
        if model is None:
            return None

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
    )

    return embeddings


def encode_single(text: str,
                  model: Optional[object] = None) -> Optional['np.ndarray']:
    """
    Encode a single text to an embedding vector.

    # Athena [Documentation]: Convenience function for single texts
    # Returns 1D array of shape (384,)
    """
    result = encode_texts([text], model=model, show_progress=False)
    if result is not None and len(result) > 0:
        return result[0]
    return None


# =============================================================================
# SIMILARITY COMPUTATION
# =============================================================================
# Kali [Visionary]: How close are two ideas?
# Athena [Reviewer]: Cosine similarity, handles edge cases
# Nemesis [Security]: Pure math, no side effects


def cosine_similarity(a: 'np.ndarray', b: 'np.ndarray') -> float:
    """
    Compute cosine similarity between two vectors.

    # Kali [Visionary]: The core of semantic comparison
    # Athena [Documentation]: Returns float in [-1, 1], typically [0, 1]
    # Nemesis [Security]: Handles zero vectors gracefully

    Args:
        a: First embedding vector
        b: Second embedding vector

    Returns:
        Cosine similarity score (0 = orthogonal, 1 = identical)
    """
    if not HAS_NUMPY:
        return 0.0

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def batch_cosine_similarity(embeddings: 'np.ndarray',
                            query: 'np.ndarray') -> 'np.ndarray':
    """
    Compute cosine similarity between query and all embeddings.

    # Kali [Visionary]: Find what resonates with a thought
    # Athena [Documentation]: Returns array of shape (n,)
    # Vesta [Builder]: Vectorized for performance

    Args:
        embeddings: Matrix of shape (n, dim)
        query: Query vector of shape (dim,)

    Returns:
        Array of similarity scores, shape (n,)
    """
    if not HAS_NUMPY:
        return np.array([])

    if len(embeddings) == 0:
        return np.array([])

    # Compute norms
    emb_norms = np.linalg.norm(embeddings, axis=1)
    query_norm = np.linalg.norm(query)

    # Handle zero vectors
    if query_norm == 0:
        return np.zeros(len(embeddings))

    # Avoid division by zero
    emb_norms = np.where(emb_norms == 0, 1e-10, emb_norms)

    # Compute similarities
    similarities = np.dot(embeddings, query) / (emb_norms * query_norm)

    return similarities


def find_top_k(embeddings: 'np.ndarray',
               query: 'np.ndarray',
               k: int = 10) -> List[tuple]:
    """
    Find top-k most similar embeddings to query.

    # Kali [Visionary]: What connects most strongly?
    # Athena [Documentation]: Returns [(index, score), ...]

    Args:
        embeddings: Matrix of shape (n, dim)
        query: Query vector of shape (dim,)
        k: Number of top results to return

    Returns:
        List of (index, similarity_score) tuples, sorted by score desc
    """
    if not HAS_NUMPY:
        return []

    similarities = batch_cosine_similarity(embeddings, query)

    # Get top-k indices
    if k >= len(similarities):
        top_indices = np.argsort(similarities)[::-1]
    else:
        # Use argpartition for efficiency on large arrays
        top_indices = np.argpartition(similarities, -k)[-k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

    return [(int(idx), float(similarities[idx])) for idx in top_indices]


# =============================================================================
# EMBEDDING UTILITIES
# =============================================================================


def get_embedding_dimension() -> int:
    """Return the embedding dimension (384 for all-MiniLM-L6-v2)."""
    return EMBEDDING_DIMENSION


def validate_embedding(embedding: 'np.ndarray') -> bool:
    """
    Validate that an embedding has the expected shape.

    # Athena [Reviewer]: Sanity check for loaded embeddings
    """
    if not HAS_NUMPY:
        return False
    if embedding is None:
        return False
    if not isinstance(embedding, np.ndarray):
        return False
    if embedding.shape[-1] != EMBEDDING_DIMENSION:
        return False
    return True


def normalize_embedding(embedding: 'np.ndarray') -> 'np.ndarray':
    """
    L2-normalize an embedding vector.

    # Vesta [Builder]: Normalized vectors make similarity = dot product
    """
    if not HAS_NUMPY:
        return embedding
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm


def compute_centroid(embeddings: 'np.ndarray') -> 'np.ndarray':
    """
    Compute the centroid (mean) of multiple embeddings.

    # Kali [Visionary]: The center of a cluster of ideas
    # Athena [Documentation]: Used for facet divergence analysis
    """
    if not HAS_NUMPY:
        return None
    if len(embeddings) == 0:
        return np.zeros(EMBEDDING_DIMENSION)
    return np.mean(embeddings, axis=0)


# =============================================================================
# VERSION INFO
# =============================================================================

__version__ = '1.0.0'
__author__ = 'Human-AI Collaboration (Nathan Batty & Paradoxa)'
__mira_attribution__ = 'MIRA concepts by Taylor Satula (github.com/taylorsatula/mira-OSS, AGPL)'
