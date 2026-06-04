"""
import_data.py
Importa movies.csv e ratings.csv do Kaggle Movie Recommendation System para o Redis.

Estruturas utilizadas:
movie:<id>                HASH
genre:<genre>             SET
top_rated                 ZSET
genre:<genre>:ranking     ZSET
recommended:list          LIST
"""

import os, csv, time, statistics
from collections import defaultdict
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

DATA_DIR     = "/import/data"
MOVIES_FILE  = os.path.join(DATA_DIR, "movies.csv")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.csv")

MAX_MOVIES  = 5_000    
MAX_RATINGS = 5_000  


def connect() -> redis.Redis:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    r.ping()
    print(f"✅  Conectado ao Redis em {REDIS_HOST}:{REDIS_PORT}")
    return r


def flush_old_data(r: redis.Redis):
    print("🗑️   Limpando dados anteriores...")
    r.flushdb()


def import_movies(r: redis.Redis) -> tuple[set[str], dict[str, str]]:
    print("🎬  Importando filmes...")

    imported_ids: set[str] = set()
    movie_genres: dict[str, str] = {}

    pipe = r.pipeline(transaction=False)
    count = 0

    with open(MOVIES_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:

            if count >= MAX_MOVIES:
                break

            mid    = row["movieId"]
            title  = row["title"]
            genres = row["genres"]

            pipe.hset(
                f"movie:{mid}",
                mapping={
                    "title": title,
                    "genres": genres
                }
            )

            for genre in genres.split("|"):
                if genre and genre != "(no genres listed)":
                    pipe.sadd(f"genre:{genre}", mid)

            imported_ids.add(mid)

            # Salva os gêneros em memória
            movie_genres[mid] = genres

            count += 1

    pipe.set("stats:total_movies", count)
    pipe.execute()

    print(f"   ✔ {count} filmes importados")

    return imported_ids, movie_genres


def import_ratings(
    r: redis.Redis,
    valid_ids: set[str],
    movie_genres: dict[str, str]
):

    print("⭐  Importando avaliações...")

    pipe = r.pipeline(transaction=False)
    count = 0

    movie_ratings: dict[str, list[float]] = defaultdict(list)

    with open(RATINGS_FILE, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            if count >= MAX_RATINGS:
                break

            uid = row["userId"]
            mid = row["movieId"]
            rat = float(row["rating"])
            ts  = row["timestamp"]

            if mid not in valid_ids:
                continue

            # Avaliação individual
            pipe.hset(
                f"rating:{uid}:{mid}",
                mapping={
                    "rating": rat,
                    "timestamp": ts
                }
            )

            # Avaliações do filme
            pipe.zadd(
                f"movie:{mid}:ratings",
                {uid: rat}
            )

            movie_ratings[mid].append(rat)

            count += 1

    pipe.set("stats:total_ratings", count)
    pipe.execute()

    print("📊  Calculando top_rated...")

    pipe2 = r.pipeline(transaction=False)

    for mid, ratings in movie_ratings.items():

        avg = statistics.mean(ratings)

        # Ranking global
        pipe2.zadd(
            "top_rated",
            {mid: avg}
        )

        # Ranking por gênero
        genres = movie_genres[mid]

        for genre in genres.split("|"):

            if genre and genre != "(no genres listed)":

                pipe2.zadd(
                    f"genre:{genre}:ranking",
                    {mid: avg}
                )

    pipe2.execute()

    print(f"   ✔ {count} avaliações importadas")

def main():
    t0 = time.time()
    r  = connect()
    flush_old_data(r)
    ids, movie_genres = import_movies(r)
    import_ratings(
        r,
        ids,
        movie_genres
    )
    elapsed = time.time() - t0
    print(f"\n🏁  Importação concluída em {elapsed:.1f}s")


if __name__ == "__main__":
    main()
