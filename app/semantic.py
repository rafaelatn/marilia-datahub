"""Local sentence embeddings for pending categorical standardization suggestions."""
import logging
import os
import tempfile
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from threading import Lock
from time import monotonic

import httpx
import numpy as np

from app.quality import cell_check

MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
REVISION = 'e8f8c211226b894fcb81acc59f3b34ba3efd5f42'
FILES = {
    'tokenizer.json': ('tokenizer.json', '2c3387be76557bd40970cec13153b3bbf80407865484b209e655e5e4729076b8'),
    'model.onnx': ('onnx/model_quint8_avx2.onnx', '98a01d88b7de996cdea58c32ca71208c09968d143798814b2ea09d3439dc334f'),
}
BATCH_SIZE = 16
MAX_TEXTS = 64
MAX_LABELS = 64
MIN_SIMILARITY = 0.72
MIN_MARGIN = 0.025
INIT_LOCK = Lock()
logger = logging.getLogger(__name__)


def download_asset(directory, name, relative_path, expected_hash):
    destination = directory / name
    if destination.is_file():
        return destination
    url = f'https://huggingface.co/{MODEL}/resolve/{REVISION}/{relative_path}'
    deadline = monotonic() + 40
    digest = sha256()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as file:
            temporary = Path(file.name)
            with httpx.stream('GET', url, follow_redirects=True, timeout=10) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    if monotonic() > deadline:
                        raise TimeoutError('Tempo limite de obtenção do modelo')
                    file.write(chunk)
                    digest.update(chunk)
        if digest.hexdigest() != expected_hash:
            raise ValueError('Arquivo do modelo não corresponde à revisão configurada')
        temporary.replace(destination)
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@lru_cache(maxsize=1)
def load_encoder():
    from onnxruntime import InferenceSession, SessionOptions
    from tokenizers import Tokenizer

    configured = os.getenv('DATAHUB_MODEL_DIR')
    directory = Path(configured) if configured else Path(tempfile.gettempdir()) / f'datahub-minilm-{REVISION[:8]}'
    directory.mkdir(parents=True, exist_ok=True)
    assets = {name: download_asset(directory, name, *details) for name, details in FILES.items()}
    tokenizer = Tokenizer.from_file(str(assets['tokenizer.json']))
    tokenizer.enable_truncation(max_length=128)
    tokenizer.enable_padding(pad_id=tokenizer.token_to_id('<pad>'), pad_token='<pad>')
    options = SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = InferenceSession(str(assets['model.onnx']), options, providers=['CPUExecutionProvider'])
    return tokenizer, session


def encode(texts):
    with INIT_LOCK:
        tokenizer, session = load_encoder()
    input_names = {tensor.name for tensor in session.get_inputs()}
    vectors = []
    for start in range(0, len(texts), BATCH_SIZE):
        tokens = tokenizer.encode_batch(texts[start:start+BATCH_SIZE])
        mask = np.asarray([token.attention_mask for token in tokens], dtype=np.int64)
        features = {
            'input_ids': np.asarray([token.ids for token in tokens], dtype=np.int64),
            'attention_mask': mask,
            'token_type_ids': np.asarray([token.type_ids for token in tokens], dtype=np.int64),
        }
        hidden = session.run(['last_hidden_state'], {key: features[key] for key in input_names})[0]
        pooled = (hidden * mask[..., None]).sum(axis=1) / mask.sum(axis=1)[:, None]
        vectors.extend(pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12))
    return np.asarray(vectors)


def enrich_issues(issues, schema):
    """Suggest domain labels for unresolved values, without changing records or scores."""
    domains = {}
    for field in schema['colunas']:
        labels = field.get('valores_permitidos', [])
        if field.get('similaridade_semantica') and 1 <= len(labels) <= MAX_LABELS:
            canonical = tuple(label for label in dict.fromkeys(labels)
                              if isinstance(label, str) and cell_check(label, field)[0] is None)
            if canonical:
                domains[field['nome_coluna']] = canonical
    groups = {}
    for issue in issues:
        text = issue.get('before')
        column = issue['column']
        if column in domains and issue.get('after') is None and isinstance(text, str) and 0 < len(text.strip()) <= 160:
            groups.setdefault((column, text), []).append(issue)
    if not groups:
        return {'status': 'sem_candidatos', 'avaliados': 0, 'sugestoes': 0}
    pairs = list(groups)[:MAX_TEXTS]
    texts = list(dict.fromkeys([text for _, text in pairs] +
                               [label for column, _ in pairs for label in domains[column]]))
    try:
        embeddings = dict(zip(texts, encode(texts), strict=True))
    except Exception as exc:
        logger.warning('Inferência MiniLM indisponível: %s', type(exc).__name__)
        return {'status': 'indisponivel', 'avaliados': 0, 'sugestoes': 0}

    count = 0
    for column, text in pairs:
        ranked = sorted(((float(embeddings[text] @ embeddings[label]), label)
                         for label in domains[column]), reverse=True)
        score, label = ranked[0]
        if score < MIN_SIMILARITY or (len(ranked) > 1 and score - ranked[1][0] < MIN_MARGIN):
            continue
        for issue in groups[column, text]:
            issue.update(after=label, method='Sentence Transformers MiniLM',
                         semantic_similarity=round(min(score, 1) * 100, 1),
                         reason='Similaridade semântica com categoria do esquema')
            count += 1
    return {'status': 'parcial' if len(groups) > len(pairs) else 'executado',
            'avaliados': len(pairs), 'sugestoes': count, 'modelo': MODEL}
