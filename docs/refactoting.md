# Plano de refatorações

Aqui as refatorações previstas serão brevemente detalhadas, a fim de que se
possa observar sua necessidade e viabilidade. Uma vez que uma refatoração
considerada necessária e viável tenha sido iniciada, aqui também se fará uma
espécie de "pré" planejamento, bem como acompanhamento e/ou relatório
simplificados.

## Isolar um arquivo de configuração para cada domínio

Acredito que isto favoreceria não só o desacoplamento, como o empacotamento,
distribuição e reaproveitamento em outros projetos de robô/análise de mercado.

## Avaliar formatação de klines em dataframes

Da maneira como está implementada, o trato com as klines depende, grosso modo,
de 2 módulos: ***.marketdata.brokers*** e ***.marketdata.klines***, além de
algumas classes - inclusive de formatação de *"datetimes"* - que estão num
módulo compartilhado ***.share.tools***. Isto requer atenção, para distribuição
correta de atribuições e interfaces, além da ingestão correta de dependência,
mantendo uma arquitetura racional, robusta, inteligível, testável, desacoplada e
portável.
