"""
demo_commands.py
Demonstra conceitos de DDL e DML no Redis usando os dados de filmes.

Redis não tem DDL formal, mas mapeamos os conceitos:
  DDL (estrutura) → criação/remoção de chaves e tipos de dados
  DML (dados)     → CRUD sobre as estruturas criadas
"""

import os, time
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

SEP = "─" * 60


def r_conn():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def secao(titulo: str):
    print(f"\n{'═'*60}")
    print(f"  {titulo}")
    print(f"{'═'*60}")


def bloco(descricao: str, comando: str, resultado):
    print(f"\n  📌 {descricao}")
    print(f"  CMD : {comando}")
    print(f"  RES : {resultado}")


# ─────────────────────────────────────────────────────────────
# DDL  –  Definição / estrutura das chaves
# ─────────────────────────────────────────────────────────────

def demo_ddl(r: redis.Redis):
    secao("DDL — Criação e Remoção de Estruturas de Dados")

    # 1. Criar Hash (equivale a CREATE TABLE + INSERT)
    mid = "999999"
    r.hset(f"movie:{mid}", mapping={"title": "Demo Film", "genres": "Action|Drama"})
    bloco(
        "HSET – cria (ou substitui) um Hash (≈ CREATE TABLE + row)",
        f"HSET movie:{mid} title 'Demo Film' genres 'Action|Drama'",
        r.hgetall(f"movie:{mid}")
    )

    # 2. Verificar tipo da chave (≈ DESCRIBE TABLE)
    bloco(
        "TYPE – inspeciona o tipo de dado da chave (≈ DESCRIBE)",
        f"TYPE movie:{mid}",
        r.type(f"movie:{mid}")
    )

    # 3. TTL / EXPIRE – ciclo de vida da chave (≈ política de retenção)
    r.expire(f"movie:{mid}", 300)
    bloco(
        "EXPIRE + TTL – define e consulta tempo de vida (≈ retenção DDL)",
        f"EXPIRE movie:{mid} 300  →  TTL movie:{mid}",
        f"{r.ttl(f'movie:{mid}')}s restantes"
    )

    # 4. PERSIST – remover TTL (tornar a chave permanente)
    r.persist(f"movie:{mid}")
    bloco(
        "PERSIST – remove o TTL, torna a chave permanente",
        f"PERSIST movie:{mid}",
        f"TTL agora: {r.ttl(f'movie:{mid}')} (-1 = sem expiração)"
    )

    # 5. RENAME – renomear chave (≈ ALTER TABLE RENAME)
    r.rename(f"movie:{mid}", f"movie:{mid}:backup")
    bloco(
        "RENAME – renomeia a chave (≈ ALTER TABLE RENAME)",
        f"RENAME movie:{mid} movie:{mid}:backup",
        r.hgetall(f"movie:{mid}:backup")
    )

    # 6. DEL – excluir a chave (≈ DROP TABLE)
    deleted = r.delete(f"movie:{mid}:backup")
    bloco(
        "DEL – exclui a chave (≈ DROP TABLE)",
        f"DEL movie:{mid}:backup",
        f"{deleted} chave(s) removida(s)"
    )

    # 7. SCAN – listar chaves por padrão (≈ SHOW TABLES LIKE)
    keys = list(r.scan_iter("movie:*", count=5))[:5]
    bloco(
        "SCAN – lista chaves por padrão (≈ SHOW TABLES LIKE 'movie%')",
        "SCAN 0 MATCH movie:* COUNT 5",
        keys
    )


# ─────────────────────────────────────────────────────────────
# DML  –  Manipulação de dados
# ─────────────────────────────────────────────────────────────

def demo_dml_strings(r: redis.Redis):
    secao("DML / String — SET, GET, INCR, APPEND, GETSET")

    # INSERT
    r.set("stats:demo_counter", 0)
    bloco("SET – cria/substitui um valor (≈ INSERT)", "SET stats:demo_counter 0", r.get("stats:demo_counter"))

    # SELECT
    total = r.get("stats:total_movies")
    bloco("GET – lê o valor (≈ SELECT)", "GET stats:total_movies", total)

    # UPDATE via INCR
    r.incr("stats:demo_counter")
    r.incrby("stats:demo_counter", 9)
    bloco("INCR/INCRBY – incremento atômico (≈ UPDATE SET x = x+N)", "INCRBY stats:demo_counter 9", r.get("stats:demo_counter"))

    # APPEND
    r.set("temp:note", "Redis")
    r.append("temp:note", " é incrível!")
    bloco("APPEND – concatena ao valor existente", "APPEND temp:note ' é incrível!'", r.get("temp:note"))

    # DELETE
    r.delete("stats:demo_counter", "temp:note")
    bloco("DEL – remove as chaves (≈ DELETE + DROP)", "DEL stats:demo_counter temp:note", "removidas")


def demo_dml_hash(r: redis.Redis):
    secao("DML / Hash — HSET, HGET, HMGET, HGETALL, HDEL")

    # Pegar primeiro filme importado
    mid = next(r.scan_iter("movie:[0-9]*"))
    mid_id = mid.split(":")[1]

    # HGETALL (SELECT *)
    dados = r.hgetall(mid)
    bloco("HGETALL – todos os campos do Hash (≈ SELECT *)", f"HGETALL {mid}", dados)

    # HMGET (SELECT campo1, campo2)
    bloco("HMGET – campos específicos (≈ SELECT title, genres)", f"HMGET {mid} title genres", r.hmget(mid, "title", "genres"))

    # HSET update (UPDATE SET)
    r.hset(mid, "popularity", 42)
    bloco("HSET – adiciona/atualiza campo (≈ UPDATE SET popularity=42)", f"HSET {mid} popularity 42", r.hget(mid, "popularity"))

    # HINCRBY
    r.hincrby(mid, "popularity", 8)
    bloco("HINCRBY – incremento em campo numérico (≈ UPDATE SET pop = pop+8)", f"HINCRBY {mid} popularity 8", r.hget(mid, "popularity"))

    # HEXISTS
    bloco("HEXISTS – verifica existência de campo (≈ IS NOT NULL)", f"HEXISTS {mid} genres", r.hexists(mid, "genres"))

    # HDEL
    r.hdel(mid, "popularity")
    bloco("HDEL – remove campo do Hash (≈ UPDATE SET popularity = NULL)", f"HDEL {mid} popularity", f"campo 'popularity' removido")


def demo_dml_sets(r: redis.Redis):
    secao("DML / Set — SADD, SMEMBERS, SCARD, SINTER, SDIFF, SREM")

    # Primeiro gênero disponível
    genre_key = next(r.scan_iter("genre:*"))
    genre = genre_key.split(":", 1)[1]

    count = r.scard(genre_key)
    bloco("SCARD – quantidade de membros (≈ COUNT(*))", f"SCARD {genre_key}", count)

    members = list(r.sscan_iter(genre_key))[:5]
    bloco("SSCAN – amostra de membros (≈ SELECT LIMIT 5)", f"SSCAN {genre_key}", members)

    # Interseção de dois gêneros (filmes em ambos os gêneros)
    keys = list(r.scan_iter("genre:*"))
    if len(keys) >= 2:
        inter = r.sinter(keys[0], keys[1])
        bloco(
            "SINTER – interseção de Sets (≈ INNER JOIN / INTERSECT)",
            f"SINTER {keys[0]} {keys[1]}",
            f"{len(inter)} filmes em ambos os gêneros"
        )
        diff = r.sdiff(keys[0], keys[1])
        bloco(
            "SDIFF – diferença de Sets (≈ EXCEPT / NOT IN)",
            f"SDIFF {keys[0]} {keys[1]}",
            f"{len(diff)} filmes exclusivos de '{keys[0]}'"
        )

    # SADD + SREM
    r.sadd("genre:Test", "111", "222")
    bloco("SADD – adiciona membros (≈ INSERT)", "SADD genre:Test 111 222", r.smembers("genre:Test"))
    r.srem("genre:Test", "111")
    bloco("SREM – remove membro (≈ DELETE WHERE)", "SREM genre:Test 111", r.smembers("genre:Test"))
    r.delete("genre:Test")


def demo_dml_sorted_set(r: redis.Redis):
    secao("DML / Sorted Set — ZADD, ZRANGE, ZREVRANGE, ZSCORE, ZRANK, ZRANGEBYSCORE")

    # Top 10 filmes por rating médio
    top = r.zrevrange("top_rated", 0, 9, withscores=True)
    print("\n  🏆 Top 10 filmes por rating médio:")
    for rank, (mid, score) in enumerate(top, 1):
        title = r.hget(f"movie:{mid}", "title") or "?"
        print(f"     {rank:2}. [{mid}] {title[:45]:<45} avg={score:.2f}")

    # ZRANGEBYSCORE – filtrar por range (≈ WHERE rating BETWEEN x AND y)
    good = r.zrangebyscore("top_rated", 4.0, 5.0, withscores=True)
    bloco(
        "ZRANGEBYSCORE – filmes com rating médio entre 4.0 e 5.0 (≈ WHERE ... BETWEEN)",
        "ZRANGEBYSCORE top_rated 4.0 5.0 WITHSCORES",
        f"{len(good)} filmes encontrados"
    )

    # ZCARD
    bloco("ZCARD – total de membros no Sorted Set", "ZCARD top_rated", r.zcard("top_rated"))

    # ZRANK de um filme específico
    mid = top[0][0] if top else None
    if mid:
        rank = r.zrevrank("top_rated", mid)
        bloco(
            "ZREVRANK – posição no ranking descendente (≈ ROW_NUMBER() OVER ORDER BY DESC)",
            f"ZREVRANK top_rated {mid}",
            f"posição #{rank+1}"
        )

    # Avaliações de um filme específico
    mid2 = top[1][0] if len(top) > 1 else (top[0][0] if top else None)
    if mid2:
        usuarios = r.zrange(f"movie:{mid2}:ratings", 0, 4, withscores=True)
        bloco(
            "ZRANGE – 5 primeiros usuários que avaliaram o filme",
            f"ZRANGE movie:{mid2}:ratings 0 4 WITHSCORES",
            usuarios
        )


def demo_dml_transactions(r: redis.Redis):
    secao("DML / Transações — MULTI / EXEC / DISCARD (≈ BEGIN / COMMIT / ROLLBACK)")

    mid = "txn_test"
    pipe = r.pipeline()
    pipe.multi()
    pipe.hset(f"movie:{mid}", mapping={"title": "Transação Demo", "genres": "Test"})
    pipe.sadd("genre:Test", mid)
    pipe.zadd("top_rated", {mid: 3.5})
    resultados = pipe.execute()
    bloco(
        "MULTI/EXEC – transação atômica (≈ BEGIN + múltiplos ops + COMMIT)",
        "MULTI → HSET → SADD → ZADD → EXEC",
        resultados
    )

    # DISCARD (rollback)
    pipe2 = r.pipeline()
    pipe2.multi()
    pipe2.set("temp:rollback", "nunca será salvo")
    pipe2.reset()   # descarta (DISCARD)
    existe = r.exists("temp:rollback")
    bloco(
        "DISCARD – cancela a transação (≈ ROLLBACK)",
        "MULTI → SET temp:rollback ... → DISCARD",
        f"chave existe? {bool(existe)}"
    )

    # Limpeza
    r.delete(f"movie:{mid}")
    r.srem("genre:Test", mid)
    r.zrem("top_rated", mid)


def demo_dml_expiry_pipeline(r: redis.Redis):
    secao("DML / Pipeline + TTL — batch de operações e expiração")

    # Pipeline batch insert
    pipe = r.pipeline(transaction=False)
    for i in range(1, 6):
        pipe.setex(f"cache:movie:{i}", 60, f"dados_em_cache_{i}")
    pipe.execute()

    keys = list(r.scan_iter("cache:movie:*"))
    ttls = {k: r.ttl(k) for k in keys}
    bloco(
        "SETEX – insere com TTL (≈ INSERT + política de expiração automática)",
        "SETEX cache:movie:N 60 'dados'  [via pipeline]",
        ttls
    )

    # OBJECT ENCODING – inspecionar representação interna
    mid = next(r.scan_iter("movie:[0-9]*"), None)
    if mid:
        enc = r.object_encoding(mid)
        bloco(
            "OBJECT ENCODING – representação interna da chave",
            f"OBJECT ENCODING {mid}",
            enc
        )

    # DEBUG SLEEP / INFO
    info_mem = r.info("memory")
    bloco(
        "INFO memory – uso de memória do servidor (≈ SHOW STATUS)",
        "INFO memory",
        {k: info_mem[k] for k in ("used_memory_human", "maxmemory_human", "mem_allocator") if k in info_mem}
    )

    r.delete(*list(r.scan_iter("cache:movie:*")))


# ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "═"*60)
    print("  🎬  Redis Movie DB — Demonstração DDL + DML")
    print("═"*60)

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    total_m = r.get("stats:total_movies")
    total_r = r.get("stats:total_ratings")
    print(f"\n  Base carregada: {total_m} filmes | {total_r} avaliações\n")

    demo_ddl(r)
    demo_dml_strings(r)
    demo_dml_hash(r)
    demo_dml_sets(r)
    demo_dml_sorted_set(r)
    demo_dml_transactions(r)
    demo_dml_expiry_pipeline(r)

    print("\n\n✅  Demonstração concluída com sucesso!\n")


if __name__ == "__main__":
    main()
