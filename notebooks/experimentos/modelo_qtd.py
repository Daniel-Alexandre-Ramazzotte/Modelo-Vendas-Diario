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
    data_min = data_referencia - timedelta(days=45)

    data_referencia_str = data_referencia.strftime('%Y-%m-%d')
    data_min_str = data_min.strftime('%Y-%m-%d')

    # === Propostas (Etapa 16), agregado diario ===
    ft_proposta = spark.table("clickhouse.crefaz.ft_proposta")

    ft_proposta = ft_proposta.filter(
        (F.col("propostaetapaid") == 16) &
        (F.col("propostadecisaoid").isNull()) &
        (F.col("ultimaalteracao").cast("date").between(
            F.date_sub(F.current_date(), 55),
            F.date_sub(F.current_date(), 1)
        ))
    )

    interval_expr = F.to_timestamp(
        F.from_unixtime((F.unix_timestamp("ultimaalteracao") /
900).cast("long") * 900)
    ).alias("Intervalo")

    ft_proposta = ft_proposta.groupBy(interval_expr).agg(
        F.sum("valor").alias("valor"),
        F.count("propostaid").alias("qntd")
    )

    ft_proposta = ft_proposta.withColumn(
        "data_hora",
        F.to_timestamp(F.split(F.col("Intervalo").cast("string"),
"\\+").getItem(0))
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

    ft_proposta = ft_proposta.withColumn("qntd",
F.col("qntd").cast("integer"))

    # dia_semana no padrao Python: Monday=0 ... Sunday=6
    ft_proposta = ft_proposta.withColumn(
        "dia_semana", ((F.dayofweek("data") + 5) % 7).cast("integer")
    )

    window_spec = Window.orderBy("data")

    ft_proposta = ft_proposta \
        .withColumn("lag_0", F.col("valor")) \
        .withColumn("lag_1", F.col("qntd")) \
        .withColumn("lag_2", F.lag("qntd", 1).over(window_spec)) \
        .withColumn("lag_3", F.lag("qntd", 2).over(window_spec)) \
        .withColumn("lag_4", F.lag("qntd", 3).over(window_spec)) \
        .withColumn("lag_5", F.lag("qntd", 4).over(window_spec)) \
        .withColumn("lag_6", F.lag("qntd", 5).over(window_spec))

      # Alvo de treino: qntd do PROXIMO dia da serie + dia_semana desse  mesmo proximo dia
      # -> mesmo par (X, y) que o walk-forward do experimento_qtd usa  em cada fold.
    ft_proposta = ft_proposta \
          .withColumn("target", F.lead("qntd", 1).over(window_spec)) \
          .withColumn("dia_semana_alvo", F.lead("dia_semana",
    1).over(window_spec))

    ft_proposta = ft_proposta.dropna(
        subset=["lag_0", "lag_1", "lag_2", "lag_3", "lag_4", "lag_5",
"lag_6"]
    ).orderBy("data")

    return ft_proposta.drop("qntd", "valor").toPandas()


def model_construct(df):
    from sklearn.pipeline import Pipeline
    from sklearn.ensemble import AdaBoostRegressor

    # linhas com alvo conhecido (todas menos a ultima, cujo "amanha" ainda nao aconteceu)
    df_treino = df.dropna(subset=["target", "dia_semana_alvo"])

    cols_model = ["dia_semana_alvo", "lag_0", "lag_1", "lag_2",
"lag_3", "lag_4", "lag_5", "lag_6"]
    X_train =  df_treino[cols_model].rename(columns={"dia_semana_alvo":
"dia_semana"})
    y_train = df_treino["target"]

    model = Pipeline(steps=[
        ("adaboostregressor", AdaBoostRegressor(
            n_estimators=100,
            learning_rate=0.01,
            loss="square",
        ))
    ])
    model.fit(X_train, y_train)

    return model


def ml_pipeline(model, df):
      # ultima linha: ainda sem "target"/"dia_semana_alvo" (dia seguinte nao observado)
    ultima_linha = df.tail(1).copy()

    tz_sp = timezone(timedelta(hours=-3))
    hoje = datetime.now(tz_sp)
    ultima_linha["dia_semana"] = hoje.weekday()

    cols_model = ["dia_semana", "lag_0", "lag_1", "lag_2", "lag_3",
"lag_4", "lag_5", "lag_6"]
    ultima_linha = ultima_linha[cols_model]

    prediction = model.predict(ultima_linha)

    return prediction[0]

#Chamada ficaria df = etl_pipeline(); model = model_construct(df);
# pred = ml_pipeline(model, df).