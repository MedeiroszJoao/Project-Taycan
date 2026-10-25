# E66 HPPC/GITT: discriminação de mecanismos, 2026-10-25

**Veredito: preferência condicional por cinética mais rápida; Etapa 4B continua em desenvolvimento.** Não foi ajustado ou promovido um novo gerador B. A falha anterior em 1C permanece registrada. Este estudo não valida falhas de motor/inversor nem diagnóstico do veículo.

## Escopo e procedência

Autorização nesta rodada: HPPC e GITT da célula E66, 25°C, Part 1. Somente esses dois novos arquivos experimentais foram analisados numericamente. Não foram abertos os módulos reservados de validação/cego ou os 1.152 testes históricos. Os dados são de uma célula; segmentos não constituem réplicas biológicas independentes.

Fonte: Uwalaka, Yao, Duque e Kollmeyer (2024), DOI [10.5683/SP3/7JP3NM](https://doi.org/10.5683/SP3/7JP3NM), CC BY 4.0. Metadados originais e explicação HPPC foram lidos antes dos resultados. Hashes dos arquivos constam em `results/e66_pulse_discrimination/*_EMPIRICAL.json`; hash do ZIP em `PROTOCOL.json`. Não se publicam arquivos brutos ou séries experimentais completas.

O protocolo, seleção por corrente/tempo/SOC e os três candidatos foram registrados localmente antes das simulações. Isso é rastreabilidade de execução local, não registro externo com carimbo de tempo independente. O fit de origem continua sendo a reconstrução **post-hoc** documentada no relatório causal anterior, e não um congelamento recuperado anterior à exposição histórica.

## Controle de qualidade e emendas

HPPC: 403.514 linhas originais, 362 repetições de tempo; 42 com diferença entre valores de sensores. Duas tentativas pararam antes de resultados físicos, preservadas em `FAILED_*`. A emenda final excluiu qualquer pulso com timestamp conflitante na janela de 300 s anterior até 300 s posterior. Restaram três dos seis candidatos por corrente/duração/SOC. Fora dessas janelas, usa-se o primeiro valor repetido apenas para integrar a corrente global; a sensibilidade primeiro versus último é 2,1363e-7 de fração SOC (0,00002136 ponto percentual). Isso não representa toda a incerteza de SOC.

GITT: 216.757 linhas originais, 25 duplicatas idênticas, nenhum conflito, seis segmentos elegíveis. Regras e três candidatos estavam congelados antes dessa leitura. GITT foi auditado empiricamente, não usado como validação preditiva simulada.

## Modelagem e resultados

SPMe/PyBaMM 26.4.2, base Chen2020 com correção OCP post-hoc anterior, capacidade efetiva 61,2598 Ah e corrente normalizada para a célula virtual de 5 Ah. Três alternativas fixas: base, ambas as cinéticas ×2, ambas as difusividades sólidas ×2. **Nenhum parâmetro foi otimizado nesta rodada.**

Pulsos HPPC: aproximadamente 65 A por 10 s, SOC proxy 70,56%, 61,12% e 32,79%, temperatura inicial 24,52–24,94°C, repouso prévio de uma hora. A predição começa com partículas uniformes; o SOC vem de contagem de carga assumindo carga inicial completa. Usa-se tensão relativa ao repouso medido e à OCV inicial modelada: o teste remove deslocamento absoluto de OCV, não valida OCV/SOC.

| Candidato | Mediana RMSE durante carga | Mediana RMSE em repouso | Melhora durante carga |
|---|---:|---:|---:|
| Base post-hoc | 62,797 mV | 3,574 mV | — |
| Cinéticas ×2 | 25,844 mV | 3,574 mV | 58,85% |
| Difusividades ×2 | 61,334 mV | 3,281 mV | 2,33% |

Cinéticas ×2 venceu nos três pulsos e satisfez o critério local de preferência (≥75% de vitórias e ≥20% de melhora mediana). A alteração não melhorou a relaxação: sob corrente nula sua contribuição imediata desaparece. A difusão tem efeito distinto, mas estes três pulsos não identificam um valor único para cada eletrodo ou excluem outras explicações físicas.

Foram concluídas **12/12 simulações**: nove combinações pulso/candidato em malha 20 e três verificações em malha 40 no pulso mediano. Diferenças máximas 20→40: 3,977 mV (base), 3,977 mV (cinética), 1,940 mV (difusão), abaixo do limite de 5 mV. Essa comparação não prova convergência global do modelo. O resultado de preferência persiste na malha 40 desse pulso.

O RMSE agregado usa a grade pré-definida, com mais amostras durante o pulso, e não uma integral ponderada pelo tempo. As métricas de carga e repouso devem ser consultadas separadamente.

## GITT e métrica em quarentena

Seis segmentos de descarga a aproximadamente 19,498 A, cinco de 1.112 s e um de 556 s. O aumento de tensão entre 1 e 300 s após o fim da descarga foi de **18,60 a 31,90 mV**. Isso é uma descrição da relaxação, sem estimativa de coeficiente de difusão ou validação de B.

**Não utilizar `recovery_fraction_60s` em `GITT_EMPIRICAL.json`.** O extrator reutilizou a queda de tensão a 10 s como denominador, inadequado a um pulso longo com mudança de SOC. O arquivo original foi preservado como recibo; `SUMMARY.json` invalida explicitamente o campo e calcula somente a diferença entre dois pontos de repouso. Nenhuma decisão científica utiliza a fração inválida. Também não interpretar a tensão pós-pulso relativa ao repouso inicial como pura polarização: inclui mudança de OCV por SOC.

## Situação das alegações

| Alegação | Decisão |
|---|---|
| Os três candidatos fixos foram executados e comparados nos pulsos elegíveis | PASS |
| A comparação de malhas no pulso mediano respeitou 5 mV | PASS |
| A cinética ×2 explica melhor a queda relativa nesses pulsos | PASS condicional ao modelo e à seleção |
| Parâmetros eletroquímicos individuais E66 identificados | INCONCLUSIVO |
| GITT validou previsões de tensão do gerador B | NÃO EXECUTADO |
| Gerador B E66 calibrado, congelado e validado independentemente | PENDENTE |
| Validade diagnóstica externa do simulador A ou aprovação 4B | NÃO DEMONSTRADA |

## Continuação necessária

A próxima implementação deve ajustar um conjunto pequeno de parâmetros identificáveis usando somente desenvolvimento (incluindo HPPC agora exposto), quantificar perfis de sensibilidade/confundimento e registrar um novo congelamento antes de qualquer avaliação reservada. O GITT já foi exposto empiricamente nesta rodada: não poderá ser chamado de holdout cego. Pode verificar dinâmica em uma sessão separada com essa limitação declarada. Os módulos reservados continuam fechados até um protocolo e modelo apropriados à topologia/instrumentação.

Reprodução: `python scripts/e66_pulse_discrimination.py HPPC`, depois `GITT`, depois `python scripts/summarize_e66_pulse_discrimination.py`. Exige ZIP licenciado no caminho declarado e recibo post-hoc de fit; guardas de hashes bloqueiam mudanças silenciosas. Versões, parâmetros e resultados constam nos recibos JSON. Testes registrados em `results/e66_pulse_discrimination/unit_tests.log`.

Verificação de código desta rodada: os cinco testes direcionados passaram (`pulse_unit_tests.log`). A descoberta global terminou sem sumário unittest (apenas 46 pontos); portanto não se declara aprovação da suíte global nesta rodada. Os 152 testes aprovados anteriormente pertencem à rodada anterior.
