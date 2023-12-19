import pandas as pd


def sortable_version(version: str) -> str:
    """
    Turn '1.1' -> '00001.00001'
    """
    return ".".join(bit.zfill(5) for bit in str(version).split("."))


def normalize_version(padded_version: str) -> float:
    """
    Turn '00001.00001' -> '1.1'
    """
    if not padded_version:
        return 0.0

    return str(float(".".join(bit.lstrip("0") for bit in padded_version.split("."))))


def parse_excluded_hgncs_from_file(file_path) -> set:
    """
    Parse hgnc file, and filter it to get genes which either are RNAs, or mitochondrially encoded.
    Currently, we do not handle these.

    Function inspired by https://github.com/eastgenomics/panel_ops/blob/main_without_docker/ops/utils.py#L1251

    :param file_path: path to hgnc file

    :return: set of HGNCs to skip
    """

    df: pd.DataFrame = pd.read_csv(file_path, delimiter="\t", dtype=str)

    df = df[
        df["Locus type"].str.contains("rna", case=False)
        | df["Approved name"].str.contains("mitochondrially encoded", case=False)
    ]

    return set(df["HGNC ID"].tolist())
