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
