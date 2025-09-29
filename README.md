# 🏛️ Kritikos: Análise Cívica Objetiva

**Kritikos** é uma plataforma dedicada a ranquear o desempenho de Deputados Federais e Partidos no Brasil, utilizando uma metodologia estritamente **quantificável** e transparente. Nosso objetivo é ir além do debate ideológico e focar na **eficácia, responsabilidade fiscal e relevância social** do trabalho legislativo.

## 🌟 O Índice de Desempenho Político (IDP)

O ranking é baseado no **Índice de Desempenho Político (IDP)**, uma nota de 0 a 100 que agrega o desempenho em quatro áreas principais:

| Eixo de Análise | Peso | Foco |
| :--- | :--- | :--- |
| **Desempenho Legislativo** | 35% | Produtividade, assiduidade e sucesso em transformar propostas em leis. |
| **Relevância Social (PAR)** | 30% | Qualidade das propostas e alinhamento com os Objetivos de Desenvolvimento Sustentável (ODS). |
| **Responsabilidade Fiscal** | 20% | Uso dos recursos de gabinete e gastos comparados à média. |
| **Ética e Legalidade** | 15% | Coerência com pareceres técnicos (CCJ) e histórico legal/processual. |

Leia a [DOCUMENTACAO_METODOLOGIA.md](docs/DOCUMENTACAO_METODOLOGIA.md) para entender em detalhes como o PAR é calculado e quais penalidades são aplicadas.

---

## 💻 Stack Tecnológica (Monorepo)

O Kritikos é construído como um monorepo simples, utilizando tecnologias modernas e otimizadas para o Free Tier:

| Componente | Tecnologia | Função |
| :--- | :--- | :--- |
| **Backend (API)** | **FastAPI** (Python 3.17.7) | Roteamento, cálculo do IDP e API de dados. |
| **Frontend (UI)** | **React** (Node 24) | Interface de usuário, visualização de rankings e gráficos. |
| **Banco de Dados** | **PostgreSQL 17** (Supabase) | Armazenamento de dados brutos e resultados dos rankings. |
| **Infraestrutura** | **Docker** e **Docker Compose** | Configuração de ambiente consistente para desenvolvimento e produção. |

---

## 🛠️ Como Rodar Localmente

Para iniciar o projeto (API, Banco de Dados local e Frontend de Desenvolvimento) você precisa ter o **Docker** e o **Docker Compose** instalados.

1.  **Clone o Repositório:**
    ```bash
    git clone [https://github.com/antoniotavarescjr/kritikos.git]
    cd kritikos
    ```
2.  **Configurar Variáveis:** Crie o arquivo `.env` na raiz do projeto com as credenciais do Postgres local (veja o guia de setup).
3.  **Subir os Containers:**
    ```bash
    docker compose up --build
    ```

Acesse o Backend em `http://localhost:8000` (docs da API) e o Frontend em `http://localhost:3000`.

---