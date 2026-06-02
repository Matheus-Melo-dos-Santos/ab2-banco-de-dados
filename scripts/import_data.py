"""
import_data.py
Importa movies.csv e ratings.csv do Kaggle Movie Recommendation System para o Redis.

Estruturas utilizadas:
  - Hash     : movie:<movieId>  → {title, genres}
  - Set      : genre:<genre>    → {movieId, ...}
  - Hash     : rating:<userId>:<movieId> → {rating, timestamp}
  - Sorted Set: movie:<movieId>:ratings → score=rating, member=userId
  - Sorted Set: top_rated        → score=avg_rating, member=movieId
  - String   : stats:total_movies / stats:total_ratings
"""

import os, csv, time, statistics
from collections import defaultdict
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

DATA_DIR     = "/import/data"
MOVIES_FILE  = os.path.join(DATA_DIR, "movies.csv")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.csv")

MAX_MOVIES  = 500    # limite para demo (retire para importar tudo)
MAX_RATINGS = 5_000  # idem


def connect() -> redis.Redis:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    r.ping()
    print(f"✅  Conectado ao Redis em {REDIS_HOST}:{REDIS_PORT}")
    return r


def flush_old_data(r: redis.Redis):
    print("🗑️   Limpando dados anteriores...")
    r.flushdb()


def import_movies(r: redis.Redis) -> set[str]:
    print("🎬  Importando filmes...")
    imported_ids: set[str] = set()
    pipe = r.pipeline(transaction=False)
    count = 0

    with open(MOVIES_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if count >= MAX_MOVIES:
                break
            mid    = row["movieId"]
            title  = row["title"]
            genres = row["genres"]          # "Action|Adventure|..."

            # ── Hash: dados do filme ──────────────────────────────
            pipe.hset(f"movie:{mid}", mapping={"title": title, "genres": genres})

            # ── Set: índice invertido por gênero ──────────────────
            for genre in genres.split("|"):
                if genre and genre != "(no genres listed)":
                    pipe.sadd(f"genre:{genre}", mid)

            imported_ids.add(mid)
            count += 1

    pipe.set("stats:total_movies", count)
    pipe.execute()
    print(f"   ✔ {count} filmes importados")
    return imported_ids


def import_ratings(r: redis.Redis, valid_ids: set[str]):
    print("⭐  Importando avaliações...")
    pipe  = r.pipeline(transaction=False)
    count = 0

    # acumular ratings por filme para calcular média depois
    movie_ratings: dict[str, list[float]] = defaultdict(list)

    with open(RATINGS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if count >= MAX_RATINGS:
                break
            uid  = row["userId"]
            mid  = row["movieId"]
            rat  = float(row["rating"])
            ts   = row["timestamp"]

            if mid not in valid_ids:
                continue

            # ── Hash: avaliação individual ────────────────────────
            pipe.hset(f"rating:{uid}:{mid}", mapping={"rating": rat, "timestamp": ts})

            # ── Sorted Set: avaliações por filme ──────────────────
            pipe.zadd(f"movie:{mid}:ratings", {uid: rat})

            movie_ratings[mid].append(rat)
            count += 1

    pipe.set("stats:total_ratings", count)
    pipe.execute()

    # ── Sorted Set global: top_rated (média ponderada) ────────────
    print("📊  Calculando top_rated...")
    pipe2 = r.pipeline(transaction=False)
    for mid, ratings in movie_ratings.items():
        avg = statistics.mean(ratings)
        pipe2.zadd("top_rated", {mid: avg})
    pipe2.execute()

    print(f"   ✔ {count} avaliações importadas")


def main():
    t0 = time.time()
    r  = connect()
    flush_old_data(r)
    ids = import_movies(r)
    import_ratings(r, ids)
    elapsed = time.time() - t0
    print(f"\n🏁  Importação concluída em {elapsed:.1f}s")


if __name__ == "__main__":
    main()
