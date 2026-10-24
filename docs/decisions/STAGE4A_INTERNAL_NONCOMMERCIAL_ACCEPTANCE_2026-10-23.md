# Etapa 4A — aceitação interna para pesquisa científica não comercial

**Data:** 2026-10-23. **Natureza:** registro de decisão do responsável pelo projeto, sem certificação automotiva e sem alegação de validação em veículo real.

## Decisão expressa pelo responsável

O responsável confirmou que o **Project Taycan é um projeto de pesquisa independente, não comercial e não monetário** e aceitou substituir a exigência de **homologação extensa/externa** por um **registro interno proporcional ao uso exclusivamente científico**. A aceitação foi confirmada em conversa em 2026-10-23 com a instrução “Ok, anote e prossigamos”.

Esta aceitação elimina qualquer *gate* artificial de certificação industrial, laboratório credenciado, contratação de engenheiro ou autorização da Porsche **para fins de pesquisa sintética**. Nenhum desses requisitos era imposto por norma externa ao projeto; eram controles internos de processo.

**Não elimina** os requisitos científicos mínimos: integridade dos arquivos, hashes, limites numéricos, consistência entre simulador/observação/features, seeds, rastreabilidade da calibração, smoke reprodutível e separação do conjunto reservado. A decisão tampouco aprova implicitamente cada alteração futura, autoriza uso em um veículo real ou altera o pré-registro histórico.

## Critério operacional simplificado para a 4A

**4A — conclusão técnica:** a versão-candidata pode ser qualificada para **experimentos sintéticos de pesquisa** quando (a) seus arquivos e parâmetros forem imutavelmente identificados, (b) o smoke de 12 hipóteses de seis horas passar com SOC 30–80%, features finitas ou ausência explicitamente mascarada, fechamento elétrico local declarado e seeds reproduzíveis, (c) I01 ativo/inativo e os perfis de carga forem declarados, (d) o pipeline/runner sucessor verificar hashes sem usar ou adaptar os resultados de teste e (e) os resultados e as ressalvas forem versionados.

**4B — validade externa:** calibração em Taycan real, PyBaMM gerador B, comparação TUM/LG E66, detectabilidade, OOD, classes ambíguas, falhas múltiplas, sensores degradados e precisão real NÃO são pré-requisitos de 4A. Seu não cumprimento limita todas as afirmações a desempenho dentro do modelo sintético.

## Evidências existentes e escopo

- O CI [40028102083](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40028102083) executou com sucesso a suite e o smoke candidato de 12×6h, incluindo o observador corrigido (auxiliar com cap no RESÍDUO, não na carga total) e I01 condicionado à operação.
- O CI [40027130137](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40027130137) registrou duas calibrações experimentais prospectivas: **47.79296875 kW** nominal e **31.5625 kW** perfil frio/regeneração, mais 12 combinações de correspondência de perda injetada M01/I01. São calibrações condicionais do gerador, não medidas reais.
- O Piloto 2 exploratório foi realizado em [40023810583](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40023810583), mas pertencia à observação anterior; não é validação da reconstrução corrigida.
- O `src/simulator/taycan_sim/model.py` histórico (SHA-256 `af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`), `freeze.json` (SHA-256 `5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8`), o manifesto de 2232 episódios e o teste reservado de 1152 episódios **não podem ser reescritos retroativamente**.
- O documento antigo `docs/decisions/STAGE4A_PROPOSED_FREEZE_2026-10-23.md` é um histórico de decisão PROPOSTA; este registro **substitui somente a exigência excessiva de homologação**, não substitui os códigos nem falsifica seu estado.

## Declaração de finalidade

“O Projeto Taycan é uma pesquisa computacional independente e não comercial. Seus modelos destinam-se à exploração de hipóteses, simulações, engenharia de software e pesquisa metodológica. A aprovação interna da Etapa 4A refere-se à integridade e à reprodutibilidade dos dados **sintéticos**, e não certifica, garante segurança, identifica falhas em veículos reais ou demonstra a fidelidade de um Porsche Taycan. Resultados fora do domínio simulado exigem validação externa específica.”

**Estado da decisão:** aceitação da via simplificada de aprovação interna **registrada**; os gates técnicos restantes serão medidos diretamente no runner sucessor. Uma falha desses gates deve ser relatada, e não contornada por esta declaração. **Não executar teste reservado antes de congelar o runner sucessor com hashes verificáveis.**
