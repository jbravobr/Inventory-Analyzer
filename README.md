# Inventory Analyzer - Versão OFFLINE 📴

Analisador de **Escrituras Públicas de Inventário e Adjudicação** para ambientes corporativos restritos.

## 🎯 O que este sistema faz

Analisa documentos PDF de inventário e extrai automaticamente:

| Cláusula | Informação Extraída | Cor no PDF |
|----------|---------------------|------------|
| **A** | Herdeiros (nome, CPF, parentesco) | 🟡 Amarelo |
| **B** | Inventariante nomeado | 🟢 Verde |
| **C** | Bens com menção a BTG | 🔵 Azul |
| **D** | Divisão dos bens BTG entre herdeiros | 🩷 Rosa |

## 📤 Saídas Geradas

1. **Relatório TXT** - Arquivo de texto com todas as informações extraídas
2. **PDF Destacado** - Documento original com marcações coloridas (marca-texto)
3. **JSON** (opcional) - Dados estruturados para integração

## 📋 Pré-requisitos

| Software | Versão | Notas |
|----------|--------|-------|
| Python | 3.14+ | Já instalado pela TI |
| Tesseract OCR | 5.x | Já instalado pela TI |
| PowerShell | 5.1+ | Nativo do Windows |
| Git + Git LFS | Última | Necessário para clonar com modelos e wheels |

## 🚀 Instalação

### 0. Instalar Git LFS (apenas uma vez por máquina)

1. Instale **Git** normalmente.
2. Instale **Git LFS** (via instalador oficial ou gerenciador de pacotes).
3. Em um terminal (PowerShell ou Git Bash), execute:

```bash
git lfs install
```

### 1. Clonar o repositório com LFS

```bash
git clone https://github.com/jbravobr/Inventory-Analyzer.git
cd Inventory-Analyzer
```

> Observação: se o Git LFS estiver instalado, os arquivos grandes (`wheels/`, `models/`, `bin/` etc.) serão baixados automaticamente.  
> Só em caso de dúvida, rode também:
>
> ```bash
> git lfs pull
> ```

### 2. Executar o instalador offline

#### 2.1. Via PowerShell (`.ps1`) – se scripts estiverem liberados

```powershell
.\install_offline.ps1
```

#### 2.2. Via Prompt de Comando (`.cmd`) – alternativa para ambientes com restrição a scripts

```bat
install_offline.cmd
```

### 3. Ativar o ambiente virtual

No PowerShell:

```powershell
.\activate_env.ps1
```

Ou no Prompt de Comando:

```bat
call venv\Scripts\activate.bat
```

Depois disso, siga para a seção **📖 Uso** abaixo.

## 📖 Uso

### Análise Completa (TXT + PDF destacado)

```powershell
python run.py analyze escritura_inventario.pdf
```

### Com diretório de saída específico

```powershell
python run.py analyze escritura_inventario.pdf -o C:\Resultados
```

### Gerar também JSON

```powershell
python run.py analyze escritura_inventario.pdf --json
```

### Apenas extrair texto (sem análise)

```powershell
python run.py extract escritura_inventario.pdf
```

### Ver configurações

```powershell
python run.py info
```

## 📁 Estrutura de Saída

Após a análise, serão gerados na pasta `output/`:

```
output/
├── escritura_inventario_relatorio_20241208_143000.txt   # Relatório TXT
├── escritura_inventario_destacado_20241208_143000.pdf   # PDF com highlights
└── escritura_inventario_resultado_20241208_143000.json  # JSON (se --json)
```

## 📝 Exemplo de Relatório TXT

```
================================================================================
                        RELATÓRIO DE ANÁLISE DE INVENTÁRIO
================================================================================

Data de Geração: 08/12/2024 14:30:00
Documento Analisado: escritura_inventario.pdf

--------------------------------------------------------------------------------
INFORMAÇÕES GERAIS
--------------------------------------------------------------------------------
Falecido (Autor da Herança): JOÃO DA SILVA
Data do Óbito: 15/03/2023
Cartório: 5º Tabelionato de Notas de São Paulo

================================================================================
CLÁUSULA A - HERDEIROS IDENTIFICADOS
================================================================================

Total de herdeiros encontrados: 3
Páginas de referência: [2, 3]
Nível de confiança: 70%

  1. MARIA DA SILVA SANTOS
     CPF: 123.456.789-00
     Parentesco: cônjuge

  2. PEDRO DA SILVA
     CPF: 234.567.890-11
     Parentesco: filho(a)

  3. ANA DA SILVA
     CPF: 345.678.901-22
     Parentesco: filho(a)

================================================================================
CLÁUSULA B - INVENTARIANTE NOMEADO
================================================================================

Nome: MARIA DA SILVA SANTOS
CPF: 123.456.789-00
É também herdeiro: SIM
Páginas de referência: [2]

================================================================================
CLÁUSULA C - BENS COM MENÇÃO A BTG
================================================================================

Total de bens BTG encontrados: 2

  BEM 1:
  ----------------------------------------
    Tipo: CDB
    Conta/Identificador: 12345-6
    Valor: R$ 150.000,00

  BEM 2:
  ----------------------------------------
    Tipo: Fundo de Investimento
    Valor: R$ 250.000,00

  VALOR TOTAL DOS BENS BTG: R$ 400.000,00

================================================================================
CLÁUSULA D - DIVISÃO DOS BENS BTG ENTRE HERDEIROS
================================================================================

  BEM: CDB - Conta 12345-6
  
  DIVISÃO:
    - MARIA DA SILVA SANTOS: 50.0% (R$ 75.000,00)
    - PEDRO DA SILVA: 25.0% (R$ 37.500,00)
    - ANA DA SILVA: 25.0% (R$ 37.500,00)
```

## 🎨 Legenda do PDF Destacado

O PDF gerado inclui uma página inicial com legenda e resumo, seguida do documento original com destaques:

- **🟡 Amarelo**: Nomes dos herdeiros
- **🟢 Verde**: Nome do inventariante
- **🔵 Azul**: Menções a "BTG" e números de conta
- **🩷 Rosa**: Percentuais de divisão

## ⚙️ Configuração

Edite `config.yaml` para ajustes:

```yaml
# Aumentar qualidade do OCR
ocr:
  dpi: 400    # Padrão: 300

# Ajustar sensibilidade da busca
rag:
  retrieval:
    top_k: 15        # Mais contexto
    min_score: 0.15  # Menos restritivo
```

## 🔧 Solução de Problemas

### Erro: "tesseract is not installed"

Verifique o caminho no `config.yaml` ou se o Tesseract está no PATH.

### Erro: "Unable to get page count"

Execute `.\activate_env.ps1` antes de usar (configura Poppler no PATH).

### PDF com highlights em branco

O documento pode ser muito longo. Tente aumentar o `top_k` no config.

### Texto extraído ilegível

Aumente o `dpi` no config.yaml para melhor qualidade de OCR.

## 📊 Tamanho do Pacote

| Componente | Tamanho |
|------------|---------|
| Wheels (Python) | ~283 MB |
| Modelos ML | ~1.8 GB |
| Poppler | ~35 MB |
| **Total** | **~2.1 GB** |

## ⚠️ Limitações

1. **OCR**: Documentos escaneados com baixa qualidade podem ter erros
2. **Extração**: Baseada em padrões - pode não encontrar todos os casos
3. **Offline**: Sem atualizações automáticas de modelos

## 📄 Licença

MIT License

