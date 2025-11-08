# Metodologia Kritikos: Versão Atual Implementada

O **Kritikos** ranqueia Deputados Federais com base em dados públicos, utilizando uma metodologia objetiva e transparente. Esta é a **versão atual implementada**, que representa uma adaptação temporária da metodologia completa.

---

## 🚨 VERSÃO TEMPORÁRIA - AVISO IMPORTANTE

Esta é uma **versão adaptada temporária** da metodologia Kritikos que **não considera** o eixo de **Ética e Legalidade** devido à indisponibilidade desses dados no momento.

**Status dos Componentes:**
- ✅ **Desempenho Legislativo** - Implementado e funcional
- ✅ **Relevância Social (PAR)** - Implementado e funcional  
- ✅ **Responsabilidade Fiscal** - Implementado e funcional
- ❌ **Ética e Legalidade** - Temporariamente desabilitado

---

## 1. Estrutura Ponderada do IDP (Versão Atual)

O IDP atual é a soma das notas obtidas em **três eixos**, com a seguinte distribuição de peso:

| Eixo de Análise | Peso (%) | Métrica Foco | Status |
| :--- | :--- | :--- | :--- |
| **Desempenho Legislativo** | **41%** | Produtividade (PLs, PECs, Emendas) e Eficácia | ✅ Ativo |
| **Relevância Social (PAR)** | **35%** | Qualidade das propostas e alinhamento com necessidades sociais | ✅ Ativo |
| **Responsabilidade Fiscal** | **24%** | Gastos de gabinete, emendas e sustentabilidade | ✅ Ativo |
| **Ética e Legalidade** | **0%** | Penalidades por má conduta e histórico processual | ❌ Desabilitado |

**Total: 100%**

---

## 2. Cálculo da Pontuação de Relevância (PAR) - ✅ Implementado

O PAR é a nota de **0 a 100** aplicada a **cada Proposta de Lei (PL/PEC)** de autoria do Deputado. A nota média dos projetos de um Deputado compõe 35% do IDP atual.

### A. Critérios Positivos (Máximo 100 pontos)

| Critério | Pontuação Máxima | O que avalia |
| :--- | :--- | :--- |
| **Escopo e Impacto** | 30 pontos | A proposta afeta positivamente a maioria da população |
| **Alinhamento com ODS** | 30 pontos | O projeto atende diretamente a pelo menos um dos ODS da ONU |
| **Inovação/Eficiência** | 20 pontos | A proposta introduz uma solução nova ou otimiza um processo |
| **Sustentabilidade Fiscal**| 20 pontos | A proposta demonstra fontes de custeio claras |

### B. Penalidade por Oneração

É aplicada uma **subtração de até 15 pontos** ao PAR se a proposta for tecnicamente insustentável financeiramente.

---

## 3. Eixos Detalhados (Versão Atual)

### 3.1 Desempenho Legislativo (41%) - ✅ Implementado

**Componentes:**
- **Quantidade de Proposições** (25 pts): 50+ proposições = excelente
- **Quantidade de Emendas** (15 pts): 20+ emendas = excelente
- **Diversidade de Tipos** (25 pts): 5+ tipos diferentes = excelente
- **Constância** (20 pts): Atividade em 6+ meses = excelente
- **Valor de Emendas** (15 pts): R$ 1M+ em emendas = excelente

### 3.2 Relevância Social (35%) - ✅ Implementado

**Componentes:**
- **Média dos PARs** das proposições não-triviais
- **Número de proposições relevantes**
- **Impacto social** das propostas analisadas

### 3.3 Responsabilidade Fiscal (24%) - ✅ Implementado

**Componentes:**
- **Análise de Proposições** (60% do peso):
  - Média de sustentabilidade fiscal das proposições
  - Penalidades por oneração aplicadas
  
- **Análise de Emendas** (40% do peso):
  - **Eficiência no Empenho** (30 pts): Taxa de empenho vs. valor total
  - **Diversificação Geográfica** (20 pts): 10+ locais atendidos = excelente
  - **Escala Responsável** (30 pts): R$ 500K a R$ 5M considerado ideal

---

## 4. O que está Faltando (Roadmap)

### 4.1 Ética e Legalidade (15% - Futuro)

Quando implementado, este eixo avaliará:

| Tipo de Penalidade | Descrição | Impacto no Ranking |
| :--- | :--- | :--- |
| **Voto Contra a CCJ** | Voto **SIM** em propostas com parecer **inconstitucional** | **-5 pontos** por votação |
| **Conflito de Interesses** | Voto a favor de propostas que beneficiam diretamente o parlamentar | **-10 pontos** por votação |
| **Situação Processual** | O político é **Réu** em Ação Penal ou Improbidade | **-30 pontos** no IDP |

### 4.2 Dados Pendentes

- **Votações em Comissão de Constituição e Justiça (CCJ)**
- **Processos judiciais e de improbidade**
- **Histórico de conflitos de interesses**
- **Conformidade técnica legislativa**

---

## 5. Fórmula Matemática (Versão Atual)

```
IDP_Atual = (Desempenho_Legislativo × 0.41) + 
            (Relevância_Social × 0.35) + 
            (Responsabilidade_Fiscal × 0.24)
```

**Fórmula Futura (quando dados disponíveis):**
```
IDP_Completo = (Desempenho_Legislativo × 0.35) + 
                (Relevância_Social × 0.30) + 
                (Responsabilidade_Fiscal × 0.20) + 
                (Ética_Legalidade × 0.15)
```

---

## 6. Implementação Técnica

### 6.1 Arquivos Principais

- **`score_calculator_adaptado.py`**: Implementação atual da metodologia
- **`pipeline_analise_agents.py`**: Análise de proposições via IA
- **`pipeline_final_integrado.py`**: Coleta de dados completa

### 6.2 Fontes de Dados

- **Proposições**: API da Câmara dos Deputados
- **Emendas**: Portal da Transparência
- **Análises PAR**: Agents de IA (Summarizer, Filter, PAR Analyzer)
- **Dados Fiscais**: APIs oficiais de gastos parlamentares

### 6.3 Banco de Dados

- **`scores_deputados`**: Tabela principal com IDP calculado
- **`analise_proposicoes`**: Resultados das análises de IA
- **`emendas_parlamentares`**: Dados completos de emendas

---

## 7. Limitações Atuais

### 7.1 Limitações Temporárias

1. **Ausência do Eixo Ético**: Sem penalidades por conduta antiética
2. **Ranking Incompleto**: Não reflete totalmente a performance parlamentar
3. **Comparabilidade Limitada**: Rankings atuais vs. futuros não diretamente comparáveis

### 7.2 Limitações Técnicas

1. **Dependência de IA**: Análises PAR dependem da qualidade dos agentes
2. **Disponibilidade de Dados**: Emendas podem ter dados incompletos
3. **Atualização em Tempo Real**: Scores precisam de recálculo periódico

---

## 8. Próximos Passos

### 8.1 Curto Prazo (1-2 meses)

- [ ] **Coletar dados de votações na CCJ**
- [ ] **Implementar parser de processos judiciais**
- [ ] **Desenvolver detector de conflitos de interesses**

### 8.2 Médio Prazo (3-6 meses)

- [ ] **Integrar eixo de Ética e Legalidade**
- [ ] **Ajustar pesos para metodologia completa**
- [ ] **Validar rankings com dados históricos**

### 8.3 Longo Prazo (6+ meses)

- [ ] **Expandir para Senadores e Partidos**
- [ ] **Implementar análise temporal (evolução)**
- [ ] **Criar dashboard público interativo**

---

## 9. Transparência e Reprodutibilidade

### 9.1 Código Aberto

- Todo o código está disponível no repositório Kritikos
- Metodologia documentada e versionada
- Cálculos reproduzíveis e auditáveis

### 9.2 Dados Públicos

- Todas as fontes de dados são oficiais e públicas
- Processamento transparente com logs detalhados
- Histórico de alterações mantido para auditoria

---

## 10. Contato e Feedback

Para dúvidas, sugestões ou reportar problemas:

- **Repositório**: https://github.com/antoniotavarescjr/kritikos
- **Documentação Completa**: `METODOLOGIA_KRITIKOS.md` (visão futura)
- **Issues**: Abrir issue no GitHub para feedback técnico

---

**Última Atualização**: Novembro 2025  
**Versão**: adaptada_v1.0  
**Próxima Versão**: completa_v2.0 (com ética e legalidade)
