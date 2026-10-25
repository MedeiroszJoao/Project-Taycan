# Etapa 4B — validação elétrica de módulo em sessões reservadas

**Parecer: PASS_LIMITED nas duas sessões de validação, para as janelas elétricas de 300 segundos pré-registradas. A Etapa 4B integral permanece sem aprovação.** Data: 25/10/2026.

Este relatório sucede o checkpoint `STAGE4B_RIGOROUS_VALIDATION_VERDICT_2026-10-25.md` quanto à instrumentação, à transferência para módulo e ao acesso aos dados de validação. O checkpoint antigo permanece como registro histórico; sua afirmação de zero acesso aos dois arquivos de validação não descreve mais o estado atual. Agora são **dois arquivos de validação analisados, quatro arquivos cegos finais sem análise numérica e zero acesso aos 1.152 episódios históricos reservados** nesta campanha.

## Evidência nova e critérios

O código, os critérios, as duas sessões permitidas e os hashes dos modelos foram publicados no commit [`fbf19bffb0622710a9e6817a6d9c059bebb0a5f8`](https://github.com/MedeiroszJoao/Project-Taycan/commit/fbf19bffb0622710a9e6817a6d9c059bebb0a5f8) antes da primeira análise numérica destas sessões pelo fluxo de trabalho. A liberação segue a regra de validação posterior com pipeline pré-registrado em `docs/decisions/STAGE4B_E66_MODULE_SPLIT_TOPOLOGY_GATE_2026-10-24.md`. Não podemos comprovar ausência de qualquer acesso humano anterior fora deste fluxo.

Após a perda dos arquivos temporários, as seis simulações foram reproduzidas a partir desse commit, sem refazer a calibração ou alterar os congelamentos. Os quatro resultados primários são:

| Sessão reservada | Modelo | RMSE por célula média | Erro máximo | Cobertura | Parecer |
|---|---|---:|---:|---:|---|
| CP alternado 1,5C | SPMe | 14,624 mV | 45,045 mV | 100% | PASS |
| CP alternado 1,5C | DFN | 13,627 mV | 43,960 mV | 100% | PASS |
| MCCC 1,5C | SPMe | 29,052 mV | 55,120 mV | 100% | PASS |
| MCCC 1,5C | DFN | 43,738 mV | 76,900 mV | 100% | PASS |

Limites pré-registrados: RMSE ≤50 mV, máximo ≤150 mV, cobertura ≥95%, proxy de SOC dentro de [0,1]. O erro é a diferença de tensão terminal AVL do módulo dividida por seis; **não é erro medido de cada célula individual**. Nenhum resultado de BMS substituiu a métrica primária AVL.

As duas verificações SPMe com malha 80 também passaram. A maior diferença entre malhas 40 e 80 foi 4,200 mV no CP e 2,873 mV no MCCC, abaixo dos 5 mV registrados. Isso é um controle localizado de refinamento SPMe, não demonstra convergência universal nem refinamento DFN.

Janelas selecionadas por regras fixas de corrente e repouso: início em 15 s no CP e 17.718 s no MCCC; duração de 300 s em ambos. O proxy de SOC variou entre 0,64463–0,64936 e 0,08279–0,21543, respectivamente. Esses valores resultam de inicialização por tensão de repouso BMS e contagem de carga: são verificações de domínio e consistência, não validação de SOC contra uma referência independente.

## Instrumentação e modelo de observação

O documento original `3-Taycan Module Instrumentation.pdf`, páginas 1 e 3, declara **6s2p**. Resolve-se a interpretação elétrica adotada, embora a descrição pública com `6p2s` deva continuar registrada como divergência documental. Os nove canais A1, A2, A3, B1, C1, D1, E1, E2 e E3 são posições de termopares na **mesma célula 4**. Não são nove células independentes. A bancada usa câmara e entrada de refrigerante a 30 °C, água/glicol 50/50 e vazão de 1,75 L/min repartida entre duas placas.

O gerador elétrico é um modelo efetivo derivado de Chen2020, com capacidade, correção de OCP e multiplicador cinético ajustados no desenvolvimento E66. Não é identificação única de todos os parâmetros dos eletrodos E66. O candidato celular está congelado desde `a4c7b8972e2dba132cc121fac1873b7fd7eb5de7`.

Uma relação explícita entre os pontos de medição foi ajustada **somente aos pares de tensões medidas AVL/BMS e corrente do ensaio de desenvolvimento 0,7C**, sem minimizar resíduos do simulador:

`V_AVL_prevista = 6 V_célula_prevista − 0,1962027898391567 + 0,0030648773038621253 I_AVL`.

A corrente AVL é positiva na carga, e a entrada celular é `−I_AVL/2`, antes da normalização da célula virtual. O adaptador foi congelado no commit `f6b9f72824dce43ccc7e15397cf4e51758b9e19b`, antes de novas previsões de desenvolvimento e da validação reservada. O coeficiente resistivo é **efetivo e empírico**; não prova resistência física de um cabo ou contato específico. O esquema completo dos circuitos de medição permanece insuficiente para essa atribuição causal.

O conjunto avaliado é, portanto, **gerador B mais adaptador de observação congelado**, condicionado à corrente medida e à inicialização por BMS. Não é previsão inteiramente livre de medições do ensaio.

## Falhas preservadas e auditoria adversarial

- O primeiro candidato cinético celular falhou no máximo de tensão C/3: 160,702 mV. A correção posterior de OCP foi exploratória, ajustada apenas em C/20 e C/3 e congelada antes das novas previsões. A falha original permanece publicada.
- A transferência direta sem adaptador falhou em CP 1C: RMSE de 64,945/66,644 mV (SPMe/DFN). Esses resultados foram reproduzidos e não substituídos pelos resultados favoráveis posteriores.
- Na seleção ingênua da primeira atividade MCCC, erros pequenos de tensão escondiam proxies de SOC acima de 1. A auditoria de domínio separada registra essa falha, preservando os gates originais, que avaliavam somente tensão. Esses trechos não são apresentados como validação de carregamento completo.
- Os registros originais têm uma linha terminal vazia. A remoção estritamente dessa linha e a verificação separada dos contadores de carga/descarga foram documentadas antes das previsões correspondentes. Falhas anteriores de ingestão permanecem nos recibos.
- O adaptador passou nos seis casos de desenvolvimento 0,7C/1C/1,2C, mas esses casos já expostos não são chamados de validação cega.
- A auditoria posterior recompôs RMSE, erro máximo, domínio de SOC e diferenças de malha a partir das previsões salvas e medições. Trata-se de recomputação separada no mesmo ambiente, não auditoria de laboratório externo.
- Um teste secundário pós-avaliação de viés constante de ±5 mV nas métricas de validação mantém o pior RMSE abaixo de 50 mV; o maior é 48,493 mV no DFN MCCC. Não equivale a campanha completa de ruído, atraso ou sensores ausentes.
- Controles celulares anteriores de inventário, SOC inicial e temperatura permanecem no checkpoint anterior. Não são extrapolados para todas as condições do módulo.

**177 testes unitários passaram, zero falhas, zero erros e zero testes ignorados** nesta reprodução. Os testes incluem restrição de acesso aos quatro arquivos cegos e rejeição de seleções incorretas de fase. Passar testes de software não substitui validação física.

## Parecer por alegação

| Alegação | Resultado científico |
|---|---|
| Topologia usada na transformação dos dados | PASS: 6s2p explicitado na instrumentação |
| Resposta elétrica nominal celular de desenvolvimento/transferência já exposta | PASS_LIMITED, não cega |
| Previsão elétrica nas duas sessões reservadas de módulo, janelas e adaptador definidos | PASS_LIMITED |
| SOC dentro dos limites do modelo nessas janelas | PASS de consistência; SOC real não validado independentemente |
| Identificação física única de parâmetros E66 ou do circuito AVL/BMS | INCONCLUSIVO |
| Generalização para outra unidade, população ou todo o carregamento | INCONCLUSIVO |
| Temperatura prevista e refrigeração real | NÃO DEMONSTRADO: modelo isoterma |
| Comparação completa A × B e transferência de 28 features/28 máscaras | NÃO DEMONSTRADO; comparação anterior limitada à lei celular 1RC |
| Validação externa dos contadores F14/F28 | NÃO DEMONSTRADO; integrar a mesma corrente/tensão seria circular |
| Falhas de bateria e sensores como classes diagnósticas | INCONCLUSIVO: sem ensaios externos rotulados de falha |
| Falhas de motor/inversor M01/I01 | FORA DO ESCOPO de SPMe/DFN |
| Diagnóstico do Taycan 4S AWD 79,2 kWh | NÃO VALIDADO |
| Aprovação integral da 4B | NÃO EMITIDA |

As temperaturas superficiais medidas variam aproximadamente de 30,01 a 34,79 °C no CP e de 29,90 a 35,57 °C no MCCC. O modelo usa a temperatura inicial fixa; os erros elétricos incluem essa aproximação. Não se reporta RMSE térmico fictício. Duas sessões do mesmo módulo não são duas unidades independentes, e centenas de amostras correlacionadas não fornecem uma amostra populacional para intervalos de confiança.

## Proveniência e reprodução

Fonte E66: Uwalaka, Yao, Duque e Kollmeyer (2024), [DOI 10.5683/SP3/7JP3NM](https://doi.org/10.5683/SP3/7JP3NM). SHA-256 do ZIP externo: `d569bb98ec52ed6b0e151e3269154063dcc4b8a13ab05b30ac7bb3fa94cfd20b`; do ZIP interno de módulo: `a5628a9d56d2e097158620346c3f69b5ff5c6269bb2770f643e91f397abcac7e`. Os hashes por sessão estão nos resultados. O recibo de ajuste celular antigo permanece identificado como reconstrução post-hoc; não foi reclassificado como congelamento original recuperado.

Resultados e logs: `results/e66_module_reserved_validation/`, `results/e66_module_observation_adapter/` e `results/e66_module_transfer/`. O manifesto `DELIVERY_SHA256.json` verifica os novos artefatos; `REPRODUCTION_ENVIRONMENT.json` registra as versões. Os dados brutos não foram republicados.

Para reproduzir a validação com o ZIP externo em `../project_sources/09-doi-10.5683-sp3-7jp3nm.zip`, instalar as versões do recibo de ambiente, copiar os dois recibos `FIT_RESULT.json` e `PROSPECTIVE.json` de `results/e66_kinetic_calibration/input_receipts/` para `results/tmp/e66_causal/receipts/e66_calibration/`, e executar:

```sh
python scripts/validate_e66_reserved_module_sessions.py run
python scripts/audit_e66_reserved_validation_results.py
PYTHONPATH=src/simulator:src:. python -m unittest discover -s tests/unit -v
```

O anexo TUM `m1774217_001.zip` falhou na disponibilização desta retomada. Não alegamos uma nova reprodução TUM nesta entrega; os números de 92 gravações/4.661.270 registros/84 janelas e a ressalva de quantização de 12 janelas continuam como evidência histórica dos relatórios anteriores, não resultados novos conferidos aqui. A configuração RWD dos dados TUM continua distinta do alvo 4S.

## Decisão de encerramento desta campanha

Foi concluída a avaliação elétrica pré-registrada do candidato congelado nas duas sessões destinadas à validação. O resultado favorável permite submeter **essa alegação delimitada** à revisão formal, preservando as falhas e limitações. A aprovação da 4B inteira não pode ser inferida desse resultado: previsão térmica, comparação completa A × B, transferência das features e evidência diagnóstica externa permanecem não demonstradas. Os quatro arquivos cegos finais, os episódios históricos, o modelo A congelado e as Etapas 5–8 não foram usados para obter aprovação artificial.
