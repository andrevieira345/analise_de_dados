from pathlib import Path
import pandas as pd


DATA_LOC = Path(__file__).resolve().parent / 'data' / 'filtered'


# Test datasets
# print(df_apr.head(5))
# print(df_ast.head(5))


"""
Filtra a tabela de asteroides com máscaras booleanas.
Filtros com valor False/None ficam desligados.

hazardous_only  -- só PHs
sentry_only     -- só objetos na lista Sentry, nao PHA mas vale a pena anotar
diameter_range  -- (min, max) em km, tamanho
classes         -- lista de classes de asteroides: "IEO", "ATE", "APO", "AMO"
max_moid        -- MOID máximo em AU
max_uncertainty -- incerteza máxima da órbita (0 a 9)
name_search     -- texto a procurar no nome
crosses_earth   -- só órbitas que cruzam a distância da órbita da Terra
"""


def filter_asteroids(
                     df,
                     hazardous_only=False,
                     sentry_only=False,
                     diameter_range = None,
                     classes = None,
                     max_moid = None,
                     max_uncertainty = None,
                     name_search = None,
                     crosses_earth = None,
                     ):
    """ Devolve só os asteroides que passam nos filtros com mascaras boleanas """

    mask = pd.Series(True, index=df.index)

    if hazardous_only:
        mask &= df["is_pha"]

    if sentry_only:
        mask &= df["is_sentry"]

    if diameter_range is not None:
        lo, hi = diameter_range
        mask &= df["diameter_km"].between(lo, hi)

    if classes is not None:
        mask &= df["orbit_class"].isin(classes)    

    if max_moid is not None:
        moid = max_moid
        mask &= df["moid_au"] <= moid

    if max_uncertainty is not None:
        mask &= (df["uncertainty"] <= max_uncertainty).fillna(False) # se NA ou nan ou NAN coloca falso

    if name_search is not None:
        mask &= df["name"].str.contains(name_search, case = False, na = False, regex = False)

    if crosses_earth:
        mask &= (df["perihelion_au"] < 1.017) & (df["aphelion_au"] > 0.983) # estes valores porque é a orbita da Terra

    return df[mask]


"""
    Filtra a tabela de aproximações com máscaras booleanas.
    Filtros com valor False/None ficam desligados.

    date_range  -- (início, fim), ex.: ("2029-01-01", "2030-01-01")
                   o fim é à meia-noite, por isso exclui o próprio dia
    bodies      -- lista de corpos: "Earth", "Moon", "Venus", "Mars", ...
    max_lunar   -- distância máxima em distâncias lunares (1 LD ≈ 384 400 km)
    future_only -- só aproximações a partir de agora
    ids         -- lista de ids de asteroides (ex.: pha["id"])
    """

def filter_approaches(
                        df,
                        date_range = None,
                        bodies = None,
                        max_lunar = None,
                        future_only = False,
                        ids = None,):

    mask = pd.Series(True, index = df.index)

    if date_range is not None:
        start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        mask &= df["date"].between(start, end)

    if bodies is not None:
        mask &= df["body"].isin(bodies)


    if max_lunar is not None:
        mask &= df["miss_lunar"] <= max_lunar

    if future_only is not False:
        mask &= df["date"] >= pd.Timestamp.now()

    if ids is not None:
        mask &= df["id"].isin(ids) 

    return df[mask]


def apr_with_ast_info(apr, ast, cols=None):
    """ Adiciona a informação do asteroide a cada aproximaçao """

    if cols is None:
        cols = ["name", "diameter_km", "is_pha", "orbit_class"]

    ast_small = ast[["id"] + cols]

    return apr.merge(ast_small, on="id", how="left")

def next_approach(apr, bodies=None):
    """ Devolve a proxima aproximacao de um asteroide """
    future = filter_approaches(apr, future_only=True, bodies=bodies)
    future = future.sort_values("date")
    nxt = future.groupby("id").first()
    return nxt.reset_index() 

def class_summary(ast):
    """Informacao das classes dos asteroides """
    summary = ast.groupby("orbit_class").agg(
        n=("id", "count"),
        pct_pha=("is_pha", "mean"), # % ph
        median_diameter_km=("diameter_km", "median"), # diametro mediano
        median_moid_au=("moid_au", "median"), # moid mediano
        median_i_deg=("i_deg", "median"), # inclinacao mediana
    )
    summary["pct_pha"] =(summary["pct_pha"] * 100).round(1)
    return summary.sort_values( "n",ascending= False )


def class_pha_crosstab(ast, normalize=False):
    if normalize:
        return (pd.crosstab(ast["orbit_class"], ast["is_pha"], normalize="index") * 100).round(1)
    return pd.crosstab(ast["orbit_class"], ast["is_pha"], margins=True)


def approaches_pivot(apr, value = "miss_lunar", aggfunc="count"):
    """ Aproximacoes por decada """
    df = apr.copy()
    df["decade"] = df["date"].dt.year // 10 * 10
    return df.pivot_table(
        index = "decade",
        columns = "body",
        values= value,
        aggfunc= aggfunc,
    )

def size_bins(ast):
    """ Categorizar asteroides conforme o tamanho"""
    df = ast.copy()
    df["size_class"] = pd.cut(
        df["diameter_km"],
        bins = [0, 0.025, 0.14, 1, float("inf")],
        labels = ["< 25m", "25m - 140m", "140m - 1km", "> 1 km" ]
    )
    summary = df.groupby("size_class", observed = True).agg(
        n = ("id", "count"),
        pct_pha = ("is_pha", "mean"),
    )
    summary["pct_pha"] = (summary["pct_pha"] * 100).round(1)
    return summary

def top_n (df, column, n = 10, largest = True, cols= None):
    """ Retorna as linhas com os maiores ou menores valores de uma coluna."""
    
    if largest:
        result = df.nlargest(n, column)
    else:
        result = df.nsmallest(n, column)

    if cols is not None:
        result = result[cols]

    return result

if __name__ == "__main__":
    pd.options.display.max_columns = 999

    df_ast = pd.read_parquet(DATA_LOC / "asteroids.parquet")
    df_apr = pd.read_parquet(DATA_LOC / "approaches.parquet")


    # =====================================TESTES=================================

    """
    # =========================TESTAR FILTROS DE def filter_asteroids=============

    print(len(df_ast))                                          # total asteroides
    print(len(filter_asteroids(df_ast, hazardous_only=True)))   # mostrar ph
    print(df_ast["is_pha"].sum())                               # contar ph


    print(filter_asteroids(df_ast, name_search="apophis")[["name", "orbit_class", "is_pha"]])
    print(len(filter_asteroids(df_ast, classes=["ATE"])))
    print(len(filter_asteroids(df_ast, classes=["ATE"], crosses_earth=True)))   # deve ser igual ao de cima
    print(len(filter_asteroids(df_ast, max_uncertainty=0)))
    """


    """
    # ==========================TESTAR FILTROS DE def filter_approaches============

    print(len(df_apr))                                                   # total de aproximações
    print(filter_approaches(df_apr, ids=["2099942"],
                            date_range=("2029-01-01", "2030-01-01")))    # Apophis em 2029: 2 linhas
    print(len(filter_approaches(df_apr, bodies=["Earth"],
                                max_lunar=1, future_only=True)))         # futuras, mais perto que a Lua

    pha = filter_asteroids(df_ast, hazardous_only=True)
    print(len(filter_approaches(df_apr, ids=pha["id"], max_lunar=1)))    # PHAs mais perto que a Lua
    """
    """
    # ==========================TESTAR def apr_with_ast_info============
    close = filter_approaches(df_apr, max_lunar=1, future_only=True)
    print(apr_with_ast_info(close, df_ast).sort_values("date").head(10))

    # ==========================TESTAR def next_approach================
    nxt = next_approach(df_apr, bodies=["Earth"])
    print(len(nxt))
    print(nxt[nxt["id"] == "2099942"])
    """

    """
    # ==========================TESTAR def class_summary================
    resumo = class_summary(df_ast)
    print(resumo)
    print("Total:", resumo["n"].sum(), "de", len(df_ast))       # devem ser iguais (ou quase)
    print("Sem classe:", df_ast["orbit_class"].isna().sum())     # explica a diferença, se houver
    """

    """
    # ==========================TESTAR def class_pha_crosstab===========
    print(class_pha_crosstab(df_ast))
    print(class_pha_crosstab(df_ast, normalize=True))
    """
    """
    # ==========================TESTAR def approaches_pivot=============
    print(approaches_pivot(df_apr))                               # n de approaches
    print(approaches_pivot(df_apr, aggfunc="median").round(1))    # mediana da distancia
    """

    """
    # ==========================TESTAR def size_bins====================
    print(size_bins(df_ast))
    print("Total:", size_bins(df_ast)["n"].sum())
    print("Sem diâmetro:", df_ast["diameter_km"].isna().sum())
    """