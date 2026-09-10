# Rust DBF corpus characterization

Generated locally from the 11 committed fixtures; no network or row values included.

| Fixture | Dataset | DBF version | Encoding | Rows | Types | First descriptor terminator | Header bytes | SHA-256 (DBC) |
|---|---|---|---|---:|---|---:|---:|---|
| sim_rr_2023_mini | sim_do | 0x03 | cp1252 | 3311 | C | 2816 | 2817 | `15b5203507161b7c35f9c69a52c955bdac133629549099b85a88e03a9a45baf0` |
| sinasc_rr_2022_mini | sinasc_nv | 0x03 | cp1252 | 13091 | C | 1984 | 1985 | `55edaa6508cb58cc35e8ce7a74d5950198d91dd3c5c4c64d9e0c8199667601db` |
| sih_rr_2024_01_mini | sih_rd | 0x03 | cp1252 | 3714 | C,N | 3648 | 3649 | `37741f8b16adcf0f19ff837f9abbf9c46af4b6c128f5599867fe0fa7940eccb5` |
| cnes_rr_2024_01_mini | cnes_st | 0x03 | cp1252 | 1036 | C,N | 6688 | 6689 | `99352c3b41d3f8f4a38d02b899460dc7b58fa5471e0ffbef83ceab4ededbfb35` |
| sia_abo_sp_2024_01_mini | sia_abo | 0x30 | latin-1 | 844 | C,N | 2528 | 2792 | `a074880b8dac172b62eed4eafb48a20d1ef6a5c398ae40125f6579b90fbe318d` |
| sia_ad_rr_2024_01_mini | sia_ad | 0x03 | latin-1 | 678 | C,N | 1504 | 1505 | `78efff648a0c6624e4c0b54fab02e8acf25cbe0c1c73a5d24bc1098b9aaff882` |
| sia_am_rr_2024_01_mini | sia_am | 0x03 | latin-1 | 2083 | C,N | 1664 | 1665 | `dbad1970271aea1a0bff0ad8006b27e17c527950cc042d268b215a375b7c22ef` |
| sia_aq_rr_2024_01_mini | sia_aq | 0x03 | latin-1 | 17 | C,N | 2400 | 2401 | `f0c8fb5e0bdbc81ed59f599e6783afcca8f30b5c3321d0509b1baf3803b60e55` |
| sia_atd_rr_2024_01_mini | sia_atd | 0x03 | latin-1 | 358 | C,N | 2112 | 2113 | `6bd7e025d6ea81cd2d515727e4679fd1f3c56b70a2841488f0ad2d651704f71e` |
| sia_bi_rr_2024_01_mini | sia_bi | 0x03 | latin-1 | 12099 | C,N | 1184 | 1185 | `80fb48c648f88c72de4e2577bfad46b8dde45dcbc029ba38c91707133f3337b2` |
| sia_ps_rr_2024_01_mini | sia_ps | 0x03 | latin-1 | 1670 | C | 1472 | 1473 | `56022bfa7245e8d57530c74e7f3144ec797c14736e94e873ba25e0ffb5c2b5d7` |

SIA ABO uses a FoxPro 0x30 header with bytes after the actual field-descriptor terminator. These bytes are not additional descriptors. CNES is passed through the existing terminator repair before either backend reads it.

Synthetic seeds in `tests/fixtures/dbf/manifest.json` cover exact int64, empty text, latin-1 0x81 and unsupported date metadata. They are shared with native Rust tests. Differential checks compare both backends; literal assertions independently protect the intended values.

Baseline resource report: `reports/rust-dbf-baseline.json` (historical materializing parser versus current bounded staging, single samples). It is not the Rust speedup report.
