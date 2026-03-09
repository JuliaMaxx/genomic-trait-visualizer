import pandas as pd


def parse_dna_file(file_path):

    df = pd.read_csv(file_path, sep="\t", comment="#")

    df = df[["rsid", "genotype"]]

    return df.to_dict(orient="records")
