# 4B — revisão de termodinâmica e eletromagnetismo
Data: 2026-10-27. Rodada de pesquisa; nenhum novo PASS experimental ou computacional.
Base: b7bde4cb1964c77ae9b049fefd3b76650e8c7694.

## Conclusão operacional
A literatura justifica priorizar memória eletroquímica, relaxação e inicialização dependente do histórico, em conjunto com balanço térmico consistente. Não demonstra a causa da falha E66 nem garante solução. Não há evidência de impossibilidade de 4B.

## Evidência interna anterior (não recalculada nesta rodada)
O candidato B congelado passa janelas elétricas curtas, mas falha no MCCC longo: aproximadamente 116 mV SPMe e 114 mV DFN contra limite RMSE de 50 mV. Temperatura superficial imposta reduz o erro, mas não o elimina.
Auditoria GITT: diferença de aproximadamente 128 mV entre históricos em baixo SOC estimado e temperaturas próximas; repousos ainda apresentam deriva. SOC depende da capacidade e estado inicial assumidos. Isso não prova histerese de equilíbrio.
As duas curvas interpoladas têm erros internos pequenos, mas não foram validadas como modelo dinâmico independente. A tensão inicial 3,152 V fica abaixo do suporte da curva de carga (~3,244 V). Isso reprova a inicialização ingênua diretamente nessa curva; não reprova uma variável de memória inicializada pelo ciclo anterior.
Nove sensores A1...E3 medem posições na superfície da mesma célula 4. Não representam nove células nem temperatura do núcleo.

## Fontes e aplicação
1. Smith & Bazant (2017), Multiphase Porous Electrode Theory, MIT:
https://dspace.mit.edu/entities/publication/34109828-c01e-40a0-8abb-73df2a4262fe
Modelo de eletrodos porosos baseado em energia livre, transporte e separação de fases. Motiva testar estados internos que não são determinados apenas pelo SOC médio. Não fornece parâmetros E66. MIT não integra formalmente a Ivy League.

2. Koo et al. (2023), Dynamic surface phases controlling asymmetry of high-rate lithiation and delithiation in phase-separating electrodes, Princeton, DOI 10.1039/d3ee00341h:
https://collaborate.princeton.edu/en/publications/dynamic-surface-phases-controlling-asymmetry-of-high-rate-lithiat/
Resultados em LixFePO4 mostram relevância de fases superficiais e cinética para assimetria direcional. Serve como hipótese mecanística, não evidência de que E66 tenha esse mecanismo: não transferir parâmetros de LFP para grafite/NMC.

3. Rashid et al. (2019), Investigation of hysteresis and relaxation behaviour in graphite and LiNi0.33Mn0.33Co0.33O2 electrodes, DOI 10.1016/j.jpowsour.2019.227153:
https://research.birmingham.ac.uk/en/publications/investigation-of-hysteresis-and-relaxation-behaviour-in-graphite-/
Estudo de meias-células diretamente relevante à família química. Histórico, SOC e duração de repouso influenciam o potencial observado. SOC de eletrodo não equivale a SOC da célula completa; amplitudes não podem ser copiadas para E66. Complementa fontes Ivy por pertinência científica.

4. MIT, Electromagnetic Fields and Energy, seções de aproximação quase-estática e condução:
https://web.mit.edu/6.013_book/www/chapter3/3.3.html
https://web.mit.edu/6.013_book/www/chapter7/7.html
Separar relaxação elétrica, propagação de campos e relaxação química. Inferência de engenharia: erro persistente em corrente quase constante torna uma explicação exclusivamente indutiva L*dI/dt menos prioritária. Ainda testar quedas resistivas, pontos de medição, distribuição de corrente e sincronização. Aproximação quase-estática não elimina gradientes elétricos nem transporte iônico.

5. PyBaMM, modelos de histerese:
https://docs.pybamm.org/en/latest/source/examples/notebooks/models/hysteresis-state-models.html
https://docs.pybamm.org/en/v26.4.0/source/api/models/submodels/interface/open_circuit_potential/one_state_hysteresis_ocp.html
Há formulações com variável de estado contínua entre ramos, incluindo one-state hysteresis e differential-capacity hysteresis. A versão latest é de desenvolvimento: conferir compatibilidade com a instalação 26.4.2 antes de implementar. Curvas de tensão da célula inteira NÃO devem ser inseridas diretamente como OCP do eletrodo positivo. Identificação por tensão terminal pode não separar os dois eletrodos de forma única.

6. PyBaMM, modelos térmicos:
https://docs.pybamm.org/en/v25.10.2/source/examples/notebooks/models/thermal-models.html
Balanço inclui fontes ôhmicas, reação irreversível, termo entrópico reversível e contato. Modelos disponíveis permitem diferentes hipóteses espaciais. Massa, volume, área de resfriamento e capacidade térmica devem corresponder à célula física; escalar corrente/capacidade de um modelo virtual de 5 Ah não valida automaticamente calor e temperatura para E66.

7. MPET, implementação oficial:
https://github.com/TRI-AMDD/mpet
https://mpet.readthedocs.io
Útil como comparação de mecanismos de separação de fases. README consultado declara falta de dependência de temperatura. Não migrar esperando resolver automaticamente o acoplamento térmico.

## Próxima sequência recomendada, antes de tocar na validação final
1. Reconstituir pré-histórico da janela de desenvolvimento e inicializar SOC, gradientes e memória. Se histórico não identificar o estado, reportar intervalo de incerteza, não ajuste oculto.
2. Reavaliar repousos por duração e deriva terminal para distinguir relaxação incompleta de separação persistente entre históricos. Testar sensibilidade à capacidade e SOC inicial.
3. Comparar baseline congelado com candidato mínimo de memória contínua. Usar a mesma corrente, portas e orçamento de calibração; evitar dupla contagem da polarização já representada no DFN/SPMe. Identificar separadamente ganho de inicialização e ganho da dinâmica.
4. Comparar resíduos em transições, corrente constante e repouso; analisar dependência de I, dI/dt, direção, SOC e temperatura. Isso discrimina hipóteses melhor que ajustar todos os parâmetros juntos.
5. Auditar unidades e balanço energético na escala E66. Um modelo núcleo/superfície pode ser candidato mínimo; só aumentar dimensão espacial se os dados sustentarem. Temperatura superficial imposta é diagnóstico, não validação térmica.
6. Se memória/relaxação forem insuficientes, testar assimetria cinética e distribuições de partículas com parâmetros identificáveis. MPET entra como estudo de mecanismo, não substituição imediata.
7. Congelar novo candidato e protocolo antes da avaliação final. Duas sessões já examinadas não voltam a ser cegas; preservar os quatro arquivos finais e os 1152 episódios históricos.

## Critérios de decisão
Redução de erro em desenvolvimento não equivale a aprovação 4B. Manter critérios elétricos existentes (RMSE 50 mV, máximo 150 mV e cobertura 95%, conforme protocolo aplicável), mais verificações térmicas e demais requisitos da etapa. Nenhum limiar é relaxado por esta revisão.
A hipótese prioritária é memória/relaxação/estado inicial; trata-se de inferência testável, não diagnóstico causal concluído.
