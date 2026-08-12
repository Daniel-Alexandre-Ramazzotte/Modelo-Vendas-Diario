JANELA_TREINO = 90  # ExtraTrees(j90): treina nas ultimas 90 obs anteriores ao dia previsto


def etl_pipeline():
    spark.conf.set("spark.sql.session.timeZone", "UTC")

    tz_sp = timezone(timedelta(hours=-3))
    hj = datetime.now(tz_sp)
    hj_str = hj.strftime('%Y-%m-%d')

    dim_calendario = spark.table("clickhouse.mis_s3.dim_calendario")

    row = dim_calendario.filter(
            (F.col("data") < F.to_date(F.lit(hj_str))) &
            (F.col("feriado") == 0) &
            (F.col("numerosemanadia") != 1)
        ) \
        .orderBy(F.col("data").desc()) \
        .select("data") \
        .first()
    data_referencia = row["data"]
    data_min = data_referencia - timedelta(days=JANELA_TREINO + 20)

    data_referencia_str = data_referencia.strftime('%Y-%m-%d')
    data_min_str = data_min.strftime('%Y-%m-%d')

    # === DATAFRAME 1: Propostas (Ingestão e Agrupamento da Etapa 16) ===
    ft_proposta = spark.table("clickhouse.crefaz.ft_proposta")

    ft_proposta = ft_proposta.filter(
        (F.col("propostaetapaid") == 16) &
        (F.col("propostadecisaoid").isNull()) &
        (F.col("ultimaalteracao").cast("date").between(
            F.date_sub(F.current_date(), JANELA_TREINO + 30),
            F.date_sub(F.current_date(), 1)
        ))
    )

    interval_expr = F.to_timestamp(
        F.from_unixtime((F.unix_timestamp("ultimaalteracao") / 900).cast("long") * 900)
    ).alias("Intervalo")

    ft_proposta = ft_proposta.groupBy(interval_expr).agg(
        F.sum("valor").alias("valor"),
        F.count("propostaid").alias("qntd")
    )

    ft_proposta = ft_proposta.withColumn(
        "data_hora",
        F.to_timestamp(F.split(F.col("Intervalo").cast("string"), "\\+").getItem(0))
    ).withColumn(
        "data",
        F.to_date("data_hora")
    )

    ft_proposta = ft_proposta.filter(
        (F.col("data") <= F.to_date(F.lit(data_referencia_str))) &
        (F.col("data") > F.to_date(F.lit(data_min_str)))
    )

    ft_proposta = ft_proposta.groupBy("data").agg(
        F.sum("qntd").alias("qntd"),
        F.sum("valor").alias("valor")
    )

    ft_proposta = ft_proposta.withColumn("qntd", F.col("qntd").cast("integer"))

    # === DATAFRAME 2: Fila (Quantidade de Propostas na Etapa 15) ===
    dbo_propostastatushistorico = spark.table("clickhouse.crefazon15m.dbo_propostastatushistorico")

    dbo_propostastatushistorico = dbo_propostastatushistorico.filter(
        (F.col("data") > F.date_sub(F.current_date(), JANELA_TREINO + 40)) &
        (F.col("data") < F.current_date())
    )

    dbo_propostastatushistorico = dbo_propostastatushistorico.groupBy(
        "propostaid",
        F.to_date("data").alias("Data")
    ).agg(
        F.max(F.struct("data", "id", "propostaetapaid")).alias("max_struct")
    ).select(
        "Data",
        "propostaid",
        F.col("max_struct.propostaetapaid").alias("etapa")
    )

    dbo_propostastatushistorico = dbo_propostastatushistorico.filter(F.col("etapa") == 15) \
                    .groupBy("Data") \
                    .agg(F.count("propostaid").alias("QUANTIDADE"))

    dbo_propostastatushistorico = dbo_propostastatushistorico.withColumnRenamed("Data", "data")

    # === JOIN: Cruzamento dos dados de Propostas (DF 1) com o Histórico de Fila (DF 2) ===
    df_merged = ft_proposta.join(dbo_propostastatushistorico, on="data", how="left")

    # dia_semana no padrao Python: Monday=0 ... Sunday=6
    df_merged = df_merged.withColumn(
        "dia_semana", ((F.dayofweek("data") + 5) % 7).cast("integer")
    )

    # Mesma tabela (cálculo dos lags de predição, sem lag fictício em lag_0, lag_1 e lag_7)
    window_spec = Window.orderBy("data")
    df_merged = df_merged \
        .withColumn("lag_0", F.col("qntd")) \
        .withColumn("lag_1", F.col("valor")) \
        .withColumn("lag_2", F.lag("valor", 1).over(window_spec)) \
        .withColumn("lag_3", F.lag("valor", 2).over(window_spec)) \
        .withColumn("lag_4", F.lag("valor", 3).over(window_spec)) \
        .withColumn("lag_5", F.lag("valor", 4).over(window_spec)) \
        .withColumn("lag_6", F.lag("valor", 5).over(window_spec)) \
        .withColumn("lag_7", F.col("QUANTIDADE"))

    # Alvo de treino: valor do PROXIMO dia da serie + dia_semana desse mesmo proximo dia
    # -> junto com lag_0..lag_7 da linha atual, forma o par (X, y) de cada fold do ExtraTrees(j90)
    df_merged = df_merged \
        .withColumn("target", F.lead("valor", 1).over(window_spec)) \
        .withColumn("dia_semana_alvo", F.lead("dia_semana", 1).over(window_spec))

    df_merged = df_merged.dropna(
        subset=["lag_0", "lag_1", "lag_2", "lag_3", "lag_4", "lag_5", "lag_6", "lag_7"]
    ).orderBy("data")

    return df_merged.drop("qntd", "valor", "QUANTIDADE").toPandas()


def model_construct(df):
    from sklearn.ensemble import ExtraTreesRegressor

    # linhas com alvo conhecido (todas menos a ultima, cujo "amanha" ainda nao aconteceu),
    # restrito a janela movel das ultimas JANELA_TREINO observacoes (ExtraTrees j90)
    df_treino = df.dropna(subset=["target", "dia_semana_alvo"]).tail(JANELA_TREINO)

    cols_model = ["dia_semana_alvo", "lag_0", "lag_1", "lag_2", "lag_3", "lag_4", "lag_5", "lag_6", "lag_7"]
    X_train = df_treino[cols_model].rename(columns={"dia_semana_alvo": "dia_semana"})
    y_train = df_treino["target"]

    model = ExtraTreesRegressor(n_estimators=300, random_state=42)
    model.fit(X_train, y_train)

    return model


def ml_pipeline(model, df):
    # Seleciona o registro mais recente (ontem)
    ultima_linha = df.tail(1).copy()

    # O dia_semana para a predição deve ser o dia de HOJE
    tz_sp = timezone(timedelta(hours=-3))
    hoje = datetime.now(tz_sp)
    ultima_linha['dia_semana'] = hoje.weekday()  # Monday=0, Sunday=6

    # Garante a ordem exata das features esperada pelo modelo
    cols_model = ['dia_semana', 'lag_0', 'lag_1', 'lag_2', 'lag_3', 'lag_4', 'lag_5', 'lag_6', 'lag_7']
    ultima_linha = ultima_linha[cols_model]

    prediction = model.predict(ultima_linha)

    return prediction[0]

# Chamada ficaria df = etl_pipeline(); model = model_construct(df); pred = ml_pipeline(model, df).
