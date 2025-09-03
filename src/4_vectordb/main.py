import os, sqlite3, json
import numpy as np
from populatevector import embed_openai

DB_FILE   = "./localvector.db"
QUERY     = "Machine-learning GenAI platform experience at Telkomsel"
TOP_K     = 5

query_vec = embed_openai(QUERY)
q_norm    = np.linalg.norm(query_vec)

con   = sqlite3.connect(DB_FILE)
cur   = con.execute("SELECT id, dim, data, l2_norm, metadata FROM vectors")

scores = []
for vid, dim, blob, v_norm, meta in cur:
    # I'll have to convert from bytes/buffer first before executing cossim
    v = np.frombuffer(blob, dtype="float32", count=dim)
    print(v_norm)
    print(type(v_norm))
    cos = float(np.dot(v, query_vec) / (v_norm * q_norm + 1e-9))
    snippet = json.loads(meta)["text"][:100] if meta else ""
    scores.append((cos, vid, snippet))

con.close()

top = sorted(scores, key=lambda x: x[0], reverse=True)[:TOP_K]

print(f"Top {TOP_K} matches for: '{QUERY}'\n")
for rank, (cos, vid, snippet) in enumerate(top, 1):
    print(f"{rank}. cosine={cos:.4f} content : {snippet}")