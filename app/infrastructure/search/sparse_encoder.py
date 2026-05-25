from typing import Any
from fastembed import SparseTextEmbedding
from qdrant_client.http import models
from app.telemetry.logger import logger

class SparseEncoder:
    """Encoder for generating sparse vectors using BM25 via fastembed."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
        return cls._instance

    @property
    def model(self) -> SparseTextEmbedding:
        if self._model is None:
            logger.info("initializing_sparse_encoder_model")
            # We use Qdrant/bm25 which is the standard BM25 model in fastembed
            self._model = SparseTextEmbedding(model_name="Qdrant/bm25")
        return self._model

    def encode(self, text: str) -> models.SparseVector:
        """Encodes a single text string into a Qdrant SparseVector."""
        if not text:
            return models.SparseVector(indices=[], values=[])
        
        # embed returns a generator, we take the first element
        embeddings = list(self.model.embed([text]))
        if not embeddings:
            return models.SparseVector(indices=[], values=[])
        
        emb = embeddings[0]
        # fastembed SparseEmbedding contains indices and values
        # We convert them to lists of native ints/floats to prevent json serialization issues
        return models.SparseVector(
            indices=[int(i) for i in emb.indices],
            values=[float(v) for v in emb.values]
        )
