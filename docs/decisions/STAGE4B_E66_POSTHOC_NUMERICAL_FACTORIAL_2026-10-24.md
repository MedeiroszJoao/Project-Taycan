# Etapa 4B — diagnóstico fatorial pós-avaliação do gerador E66 congelado

Data: 2026-10-24. **Retrospectivo**: a falha de 1C já era conhecida; este protocolo investiga sua causa, não serve para alterar critérios ou ressuscitar um PASS da avaliação original.

**Pré-condições:** os JSON originais do Work `FIT_RESULT.json`, `GENERATOR_B_FREEZE.json`, `EVALUATION.json`, `PROSPECTIVE.json`, sem edições, assinados por SHA-256. O arquivo de dados originais E66 já usado no 1C de avaliação deve coincidir com o SHA-256 de arquivo ZIP e do registro individual presentes nos recibos. Nunca tocar nos 1.152 testes históricos, nos outros ensaios celulares cegos ou nas medições de validação de módulo.

**Hipótese operacional:** na implementação atual, mudar `mesh` simultaneamente muda as tolerâncias IDAKLU. Para identificar o efeito isolado de cada fator, fixar parâmetros eletroquímicos, inicialização, protocolo de corrente, interpolação temporal, temperatura observada prescrita, condições de contorno e versão de software. Executar para cada `kind` em SPMe e DFN:
- **A (baseline original):** mesh=20, rtol=1e-6, atol=1e-7.
- **B (somente refinamento espacial):** mesh=40, rtol=1e-6, atol=1e-7.
- **C (somente tolerâncias do solver):** mesh=20, rtol=1e-8, atol=1e-9.
- **D (ambos alterados):** mesh=40, rtol=1e-8, atol=1e-9, para reproduzir comparação originalmente relatada.
- **Controle adicional de reprodutibilidade:** comparar diretamente A com o traço `EVALUATION.json` original, exigindo mesma malha temporal e <=1e-5V de diferença máxima. Se falhar, não afirmar que reproduziu a execução congelada.

Calcular RMSE e diferença máxima A×B, A×C, A×D, B×D e C×D usando um grid comum de 500 pontos somente enquanto ambas soluções existem. **Todas as comparações têm também de reportar cobertura do tempo originalmente exigido por ambas trajetórias, tempo de terminação, porcentagem comum e motivo da terminação.** Não classificar como PASS se qualquer solução encerra antes de 95% do tempo declarado; *um erro pequeno em prefixo incompleto não significa convergência*.

Calcular erro preditivo de tensão para cada solução nas mesmas 500 datas até a terminação. Salvar bias, RMSE, máximo erro e cobertura por modelo, sem retunar parâmetros. A diferença A×D pode identificar se o gap original foi reproduzido, mas **não deve substituir os critérios e vereditos originalmente congelados** (RMSE<50mV, máximo<150mV, cobertura>=95%, refinamento<=5mV). A curva E66 1C continuará FAIL sob os limiares de acurácia relatados independentemente da decomposição numérica.

A análise é identificabilidade computacional retrospectiva para **uma célula e um experimento**: nenhum bootstrap iid por linha, nenhuma conclusão OEM ou sobre classes de falhas. Se artefatos não aparecerem, status `BLOCKED_MISSING_ORIGINAL_WORK_RECEIPTS`; não regenerar silenciosamente fitting histórico com resultados inspecionados.

Implementação: `scripts/diagnose_e66_1c_frozen_numerics.py`. Fonte congelada `scripts/fit_e66_generator_b.py` permanece absolutamente inalterada.
