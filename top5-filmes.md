# Sistema de Recomendação de Filmes com Redis

## Objetivo

Demonstrar conceitos de manipulação de dados em Redis utilizando exclusivamente a CLI (`redis-cli`), simulando um sistema simples de recomendação de filmes baseado no dataset Movie Recommendation System.

Durante a demonstração serão explorados:

- Busca por gênero;
- Ordenação por avaliação;
- Criação de listas de recomendação;
- Remoção e inserção de elementos;
- Indexação de novos registros.

---

# Estrutura dos Dados

## Filmes

Cada filme é armazenado em um Hash.

Exemplo:

```redis
HGETALL movie:1
```

Resultado:

```text
title
Toy Story (1995)

genres
Adventure|Animation|Children|Comedy|Fantasy
```

---

## Índices por Gênero

Cada gênero é armazenado em um Set.

Exemplo:

```redis
SMEMBERS genre:Action
```

Resultado:

```text
1
5
18
45
```

Cada valor corresponde ao ID de um filme.

---

## Ranking de Avaliações

Os filmes são classificados em um Sorted Set.

Chave:

```text
movies:ranking
```

Exemplo:

```redis
ZREVRANGE movies:ranking 0 4 WITHSCORES
```

---

## Lista de Recomendados

Lista criada dinamicamente.

Chave:

```text
recommended:list
```

---

# Parte 1 – Consultar Filmes de um Gênero

Neste exemplo será utilizado o gênero Action.

Consultar os IDs:

```redis
SMEMBERS genre:Action
```

Exemplo de saída:

```text
1
5
18
45
```

Consultar os detalhes de um filme:

```redis
HGETALL movie:1
```

Saída:

```text
title
Toy Story (1995)

genres
Adventure|Animation|Children|Comedy|Fantasy
```

para visualizar apenas o titulo do filme

```redis
HGET movie:1 title
```

Saída

```
Toy Story (1995)
```


Como o processo de visualização dos nomes elemento a elemento é inviável de maneira manual, será utilizado um script em Lua para juntar esses dois processos. Ou seja, seria um analogo de (**SMEMBERS genre:Action**) | (**HGET movie:id title**).


```
EVAL "local ids = redis.call('SMEMBERS', 'genre:'..ARGV[1]); 
      local titles = {};
      for _, id in ipairs(ids) 
      do 
        table.insert(titles, redis.call('HGET', 'movie:'..id, 'title'))
      end;
      return titles" 0 Action
```

---

# Parte 2 – Obter os 5 Filmes Mais Bem Avaliados

Consultar o ranking:

```
ZREVRANGE genre:Action:ranking 0 4 WITHSCORES
```

Para adicionar em uma lista 

```
RPUSH recommended:list <id>
```

Script Lua criando a lista e exibindo os dados

```
EVAL "
    local top = redis.call(
        'ZREVRANGE',
        'genre:'..ARGV[1]..':ranking',
        0,
        4,
        'WITHSCORES'
    )

    redis.call('DEL', 'recommended:list')

    local res = {}

    for i=1,#top,2 do

        local movieId = top[i]
        local score = top[i+1]

        redis.call(
            'RPUSH',
            'recommended:list',
            movieId
        )

        local title = redis.call(
            'HGET',
            'movie:'..movieId,
            'title'
        )

        table.insert(
            res,
            score .. ' | ' .. title
        )
    end

    return res" 0 Action
```

---

# Parte 3 – Removendo Elementos da lista

```
RPOP recommended:list
```

Visualizar a lista:

```
LRANGE recommended:list 0 -1
```

Em Lua

```
EVAL "
    local top = redis.call(
        'LRANGE',
        'recommended:list',
        0,
        -1
    )

    local res = {}

    for i=1,#top do

        local movieId = top[i]

        local title = redis.call(
            'HGET',
            'movie:'..movieId,
            'title'
        )

        table.insert(
            res,
            movieId .. ' | ' ..
            title
        )
    end

    return res" 0
```

---

# Parte 4 – Inserir um Novo Filme

Criar um novo filme:

```
HSET movie:999999 title "10 na AB2 de Banco de Dados" genres "Action|Comedy|Sci-Fi|Horror"
```

Verificar:

```redis
HGETALL movie:999999
```

---

# Parte 5 – Criar Indexação por Gênero

Adicionar ao índice Sci-Fi:

```redis
SADD genre:Sci-Fi 999999
```

Verificar:

```redis
SMEMBERS genre:Sci-Fi
```

Saída esperada:

```
...
999999
```

---

# Parte 6 – Inserir no Ranking

Adicionar ao ranking global:

```
ZADD top_rated 10.00 999999
```

Adiciona ao ranking dos gêneros Action, Comedy, Horror, Sci-Fi

```
ZADD genre:Action:ranking 10.00 999999
ZADD genre:Comedy:ranking 10.00 999999
ZADD genre:Horror:ranking 10.00 999999
ZADD genre:Sci-Fi:ranking 10.00 999999
```

---

# Parte 7 – Inserir na Lista de Recomendados

Adicionar ao final da lista:

```redis
RPUSH recommended:list 999999
```

Visualizar:

ID
```
LRANGE recommended:list 0 -1
```

ID + Título
```
EVAL "
    local top = redis.call(
        'LRANGE',
        'recommended:list',
        0,
        -1
    )

    local res = {}

    for i=1,#top do

        local movieId = top[i]

        local title = redis.call(
            'HGET',
            'movie:'..movieId,
            'title'
        )

        table.insert(
            res,
            movieId .. ' | ' ..
            title
        )
    end

    return res" 0
```

---

# Estruturas Redis Utilizadas

| Estrutura | Finalidade |
|------------|------------|
| Hash | Armazenamento dos filmes |
| Set | Indexação por gênero |
| Sorted Set | Ranking por avaliação |
| List | Lista de recomendados |

---


# Conclusão

A demonstração apresenta:

1. Consulta por gênero utilizando Sets.
2. Ranking utilizando Sorted Sets.
3. Criação de listas de recomendação utilizando Lists.
4. Inserção e remoção de elementos.
5. Atualização de índices.
