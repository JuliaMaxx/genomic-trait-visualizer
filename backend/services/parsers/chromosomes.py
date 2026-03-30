VALID_CHROMOSOMES = {str(i) for i in range(1, 23)} | {"X", "Y", "MT", "M"}


def normalize_chromosome(chrom: str) -> str:
    chrom = chrom.strip().upper()
    if chrom == "M":
        return "MT"
    return chrom
