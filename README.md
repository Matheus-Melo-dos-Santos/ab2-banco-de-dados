# Redis Movie Recommendation DB 🎬

Dataset: [Movie Recommendation System – Kaggle](https://www.kaggle.com/datasets/parasharmanas/movie-recommendation-system)

## Estrutura do projeto

```
redis-movies/
├── docker-compose.yml      # Redis + importer
├── data/                   # ← coloque aqui os CSVs do Kaggle
│   ├── movies.csv
│   └── ratings.csv
└── scripts/
    ├── import_data.py      # importação dos CSVs para o Redis
    └── demo_commands.py    # demonstração DDL + DML
```

## Passo a passo

### 1. Baixe o dataset

Do Kaggle, extraia os dois arquivos para a pasta `data/`:

```bash
# após o download do zip do Kaggle:
unzip archive.zip -d data/
# ou copie manualmente movies.csv e ratings.csv para ./data/
```

### 2. Suba os containers

```bash
docker compose up
```

O `importer` irá:
1. Aguarda verificação da inicialização correta do container
2. Executar `import_data.py` → carrega filmes e avaliações

### 3. Explorar manualmente via redis-cli

```bash
# conectar ao Redis em execução
docker exec -it redis_movies redis-cli
```

```
# ver todas as chaves (cuidado em prod)
KEYS *

# detalhes de um filme
HGETALL movie:1

# filmes do gênero Action
SMEMBERS genre:Action

# top 5 filmes por rating médio
ZREVRANGE top_rated 0 4 WITHSCORES

# avaliações de um filme específico
ZRANGE movie:1:ratings 0 -1 WITHSCORES
```

### 4. Parar e remover volumes

```bash
docker compose down -v   # -v remove o volume redis_data
```

---

## Mapeamento DDL / DML → Redis

| Conceito SQL         | Equivalente Redis                       |
|----------------------|-----------------------------------------|
| CREATE TABLE         | HSET (criação implícita do Hash)        |
| DROP TABLE           | DEL chave                               |
| ALTER TABLE RENAME   | RENAME chave nova_chave                 |
| DESCRIBE / SHOW      | TYPE, OBJECT ENCODING, INFO             |
| INSERT               | SET / HSET / SADD / ZADD                |
| SELECT               | GET / HGETALL / SMEMBERS / ZRANGE       |
| UPDATE               | HSET campo novo_valor / INCR / APPEND   |
| DELETE               | DEL / HDEL / SREM / ZREM                |
| WHERE … BETWEEN      | ZRANGEBYSCORE                           |
| INNER JOIN           | SINTER                                  |
| EXCEPT / NOT IN      | SDIFF                                   |
| COUNT(*)             | SCARD / ZCARD                           |
| ROW_NUMBER() OVER …  | ZRANK / ZREVRANK                        |
| BEGIN / COMMIT       | MULTI / EXEC                            |
| ROLLBACK             | DISCARD                                 |
| Retenção / TTL       | EXPIRE / SETEX / PERSIST                |

## Estruturas de dados utilizadas

| Chave                      | Tipo        | Conteúdo                              |
|----------------------------|-------------|---------------------------------------|
| `movie:<id>`               | Hash        | title, genres                         |
| `genre:<nome>`             | Set         | movieIds nesse gênero                 |
| `rating:<uid>:<mid>`       | Hash        | rating, timestamp                     |
| `movie:<id>:ratings`       | Sorted Set  | score = rating, member = userId       |
| `top_rated`                | Sorted Set  | score = avg_rating, member = movieId  |
| `stats:total_movies`       | String      | contagem total                        |
| `stats:total_ratings`      | String      | contagem total                        |