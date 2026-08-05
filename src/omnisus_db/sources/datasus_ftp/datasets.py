"""Per-dataset configuration for the generic runner."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    partition_by: tuple[str, ...]
    monthly: bool = False


REGISTRY: dict[str, DatasetConfig] = {
    "sim_do": DatasetConfig(name="sim_do", partition_by=("ano", "uf")),
    "sinasc_nv": DatasetConfig(name="sinasc_nv", partition_by=("ano", "uf")),
    "sih_rd": DatasetConfig(name="sih_rd", partition_by=("ano", "uf", "mes"), monthly=True),
    "sia_bi": DatasetConfig(name="sia_bi", partition_by=("ano", "uf", "mes"), monthly=True),
    "cnes_st": DatasetConfig(name="cnes_st", partition_by=("ano", "mes"), monthly=True),
}


def get_config(dataset: str) -> DatasetConfig:
    if dataset not in REGISTRY:
        raise ValueError(f"unknown dataset: {dataset}")
    return REGISTRY[dataset]
