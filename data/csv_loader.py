import pandas as pd


def load_csv_data(path):
    df = pd.read_csv(path)
    return df.to_dict(orient="records")
