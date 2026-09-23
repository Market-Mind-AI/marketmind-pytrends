from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def stale_cutoff(days: int) -> datetime:
    """O instante antes do qual um dado coletado conta como vencido — COM fuso.

    `utc_now()` devolve sem fuso, e as colunas `created_at` deste serviço são
    `timestamp with time zone`: comparar um com o outro é `TypeError: can't
    compare offset-naive and offset-aware datetimes`. Esse erro exato derrubou
    o `/freshness` do OECD e o do World Bank, cada um de uma vez, e os dois
    passaram semanas sem que nada acusasse — o job só aparecia como um pod em
    `Error` numa listagem que ninguém abria.

    Por isso este corte nasce ciente do fuso, e não convertido depois.
    """
    return datetime.now(UTC) - timedelta(days=days)


def elapsed_ms(start: datetime) -> int:
    delta = utc_now() - start
    return int(delta.total_seconds() * 1000)
