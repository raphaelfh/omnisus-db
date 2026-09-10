"""The 18 categories requested from the DATASUS portal, with learning prompts.

Endpoints and FTP roots were verified on 2026-09-10. Seeds are suggestions;
actual filenames and sizes must come from a current directory listing.
"""

from dataclasses import asdict, dataclass

PORTAL = "https://datasus.saude.gov.br/transferencia-de-arquivos/"
PORTAL_API = "https://datasus.saude.gov.br/wp-content/ftp.php"
PORTAL_SCRIPT = "https://datasus.saude.gov.br/wp-content/transferencia.js"


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    kind: str
    subtype: str
    year: int | None
    uf: str
    directory: str
    question: str
    limitation: str
    modality: str = "1"

    def as_dict(self):
        return asdict(self)


SOURCES = (
    Source(
        "DATASUS",
        "Aplicativos TABWIN/TABNET",
        "aplicativo",
        "TABWIN",
        None,
        "BR",
        "/tabwin/tabwin",
        "Quais mapas, documentos e programas acompanham o tabulador?",
        "O pacote TABWIN representa esta categoria; não é uma base de pacientes. Executáveis não são executados.",
        "3",
    ),
    Source(
        "IBGE",
        "Base Populacional",
        "população",
        "POPT",
        2023,
        "BR",
        "/dissemin/publicos/IBGE/POPTCU",
        "Quais códigos municipais e valores populacionais estão publicados?",
        "POPT é o produto distribuído pelo DATASUS. Tabelas BR e por UF se sobrepõem; não some as duas coberturas.",
    ),
    Source(
        "Base Territorial",
        "Mapas e conversões para tabulação",
        "território",
        "TER",
        None,
        "",
        "/territorio/tabelas/2026",
        "Que tabelas relacionam municípios, UFs e regiões?",
        "A edição territorial da amostra é explícita; códigos mudam entre edições. O ZIP de tabelas não cobre todos os mapas.",
        "4",
    ),
    Source(
        "CIH",
        "Comunicação de Informação Hospitalar",
        "registros",
        "CR",
        2010,
        "RR",
        "/dissemin/publicos/CIH/200801_201012/Dados",
        "Como são descritas as comunicações hospitalares históricas?",
        "Acervo histórico. Ausência de RR no recorte não significa ausência da base.",
    ),
    Source(
        "CIHA",
        "Comunicação Hospitalar e Ambulatorial",
        "registros",
        "CIHA",
        2023,
        "RR",
        "/dissemin/publicos/CIHA/201101_/Dados",
        "Que campos distinguem os atendimentos comunicados?",
        "Disponibilidade varia por UF e competência. Não equiparar a cobertura à do SIH.",
    ),
    Source(
        "CNES",
        "Cadastro Nacional de Estabelecimentos de Saúde",
        "cadastro",
        "ST",
        2023,
        "RR",
        "/dissemin/publicos/CNES/200508_/Dados/ST",
        "Que atributos descrevem um estabelecimento na competência?",
        "A amostra ST cobre estabelecimentos; outros subtipos, como equipes e leitos, não são amostrados.",
    ),
    Source(
        "ESUSNOTIFICA",
        "e-SUS Notifica: Doença de Chagas Crônica",
        "notificações",
        "DCCR",
        2023,
        "BR",
        "/dissemin/publicos/ESUSNOTIFICA/DADOS/FINAIS",
        "Como o arquivo representa as notificações de DCC?",
        "Preservar a modalidade informada pelo portal; não confundir Chagas crônica com Chagas aguda do SINAN.",
    ),
    Source(
        "PCE",
        "Controle da Esquistossomose",
        "registros",
        "PCE",
        2023,
        "AL",
        "/dissemin/publicos/PCE/DADOS",
        "Quais campos descrevem as atividades de controle?",
        "Amostra AL; a unidade de registro e os denominadores exigem o dicionário do programa.",
    ),
    Source(
        "PO",
        "Painel de Oncologia",
        "registros",
        "PO",
        2023,
        "BR",
        "/dissemin/publicos/PAINEL_ONCOLOGIA/DADOS",
        "Que variáveis permitem estudar diagnóstico e tratamento?",
        "Recorte nacional; contagens de registros não devem ser interpretadas automaticamente como pessoas únicas.",
    ),
    Source(
        "RESP",
        "Notificações de casos suspeitos de SCZ",
        "notificações",
        "RESP",
        2023,
        "RR",
        "/dissemin/publicos/RESP/DADOS",
        "Que campos constam da notificação e da investigação?",
        "Amostras estaduais podem ter pouquíssimas linhas. Suspeita não equivale a caso confirmado.",
    ),
    Source(
        "SIASUS",
        "Informações Ambulatoriais do SUS",
        "produção",
        "PA",
        2023,
        "RR",
        "/dissemin/publicos/SIASUS/200801_/Dados",
        "Como os registros de produção ambulatorial são estruturados?",
        "PA é um subtipo da família SIA. Quantidade aprovada, registros e pessoas são medidas distintas.",
    ),
    Source(
        "SIHSUS",
        "Informações Hospitalares do SUS",
        "produção",
        "RD",
        2023,
        "RR",
        "/dissemin/publicos/SIHSUS/200801_/Dados",
        "Quais campos descrevem uma AIH reduzida?",
        "RD é um subtipo; uma AIH não deve ser tratada automaticamente como uma pessoa única.",
    ),
    Source(
        "SIM",
        "Informações de Mortalidade",
        "registros",
        "DO",
        2023,
        "RR",
        "/dissemin/publicos/SIM/CID10/DORES",
        "Como inspecionar campos de data, residência e causas?",
        "Amostra DORES. As primeiras linhas não representam a população e não permitem estimar taxas.",
    ),
    Source(
        "SINAN",
        "Agravos de Notificação",
        "notificações",
        "CHAG",
        2023,
        "BR",
        "/dissemin/publicos/SINAN/DADOS/PRELIM",
        "Como se organiza uma ficha de Chagas aguda?",
        "Uma amostra de CHAG não cobre os demais agravos. A modalidade preliminar/final acompanha a origem.",
    ),
    Source(
        "SINASC",
        "Nascidos Vivos",
        "registros",
        "DN",
        2023,
        "RR",
        "/dissemin/publicos/SINASC/1996_/Dados/DNRES",
        "Quais campos descrevem nascimento e características maternas?",
        "Amostra DNRES; comparar edições exige verificar alterações do esquema.",
    ),
    Source(
        "SISCOLO",
        "Câncer do Colo de Útero",
        "exames",
        "CC",
        2013,
        "RR",
        "/dissemin/publicos/SISCAN/SISCOLO4/Dados",
        "Que variáveis descrevem os exames citopatológicos?",
        "Acervo histórico CC. O portal pode rotular a fonte como SIASUS; mantemos também a categoria solicitada.",
    ),
    Source(
        "SISMAMA",
        "Câncer de Mama",
        "exames",
        "CM",
        2013,
        "RR",
        "/dissemin/publicos/SISCAN/SISMAMA/Dados",
        "Que campos descrevem a citopatologia de mama?",
        "Acervo histórico CM. Um arquivo existente pode estar vazio; tentativas sem linhas são registradas.",
    ),
    Source(
        "SISPRENATAL",
        "Monitoramento do Pré-Natal",
        "registros",
        "PN",
        2013,
        "RR",
        "/dissemin/publicos/SISPRENATAL/201201_/Dados",
        "Quais variáveis descrevem o acompanhamento pré-natal?",
        "Recorte histórico PN; não deve ser interpretado como retrato da atenção pré-natal atual.",
    ),
)
BY_KEY = {source.key: source for source in SOURCES}


def portal_types(script: str):
    """Read static object fields from the portal source, without executing JavaScript."""
    import re

    rows = []
    for block in re.findall(r"\{([^{}]*)\}", script):
        fields = dict(re.findall(r'(\w+)\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', block))
        if {"fonte", "sigla_arquivo", "desc_arquivo"} <= fields.keys():
            rows.append(
                {
                    key: fields.get(key)
                    for key in ("fonte", "sigla_arquivo", "desc_arquivo", "abrangencia")
                }
            )
    if not rows:
        raise ValueError("O formato das definições do portal mudou; nenhum subtipo reconhecido.")
    return rows
