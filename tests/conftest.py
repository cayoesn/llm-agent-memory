import sys
import types
from unittest.mock import MagicMock

# Stub fastembed if not present in the test environment
if "fastembed" not in sys.modules:
    fastembed_mock = types.ModuleType("fastembed")
    class SparseTextEmbedding:
        def __init__(self, *args, **kwargs):
            pass
        def embed(self, texts):
            class Emb:
                indices = [1, 2]
                values = [0.5, 0.8]
            return [Emb()]
    fastembed_mock.SparseTextEmbedding = SparseTextEmbedding
    sys.modules["fastembed"] = fastembed_mock
