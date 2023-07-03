def sortable_version(version: str) -> str:
    """
    Turn '1.1' -> '00001.00001'
    """
    return ".".join(bit.zfill(5) for bit in version.split("."))


def normalize_version(padded_version: str) -> str:
    """
    Turn '00001.00001' -> '1.1'
    """
    return ".".join(bit.lstrip("0") for bit in padded_version.split("."))
