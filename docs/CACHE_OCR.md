# Cache de OCR

O Document Analyzer possui um sistema de cache para extracoes OCR que evita o reprocessamento custoso de documentos PDF ja lidos anteriormente.

## Visao Geral

Quando um PDF e processado pela primeira vez, o texto extraido via OCR e armazenado em cache. Nas proximas vezes que o mesmo documento for processado, o texto e recuperado do cache instantaneamente.

### Beneficios

- **Velocidade**: Documentos em cache carregam em segundos vs minutos
- **Recursos**: Evita uso repetido de CPU/GPU para OCR
- **Consistencia**: Mesmo texto extraido sempre

---

## Como Funciona

### Identificacao do Documento

O cache usa o **hash SHA-256** do conteudo do PDF:

- Mesmo arquivo = mesmo cache
- Arquivo modificado = novo cache
- Nome diferente, mesmo conteudo = mesmo cache

### Estrutura do Cache

```
cache/
└── ocr/
    ├── index.json           # Indice com metadados
    ├── a1b2c3d4e5f6.json   # Texto extraido (hash truncado)
    ├── f6e5d4c3b2a1.json   # Outro documento
    └── ...
```

### Validade

- **Padrao**: 30 dias (720 horas)
- **Configuravel**: Via config.yaml
- **Limpeza**: Manual ou automatica

---

## Comandos CLI

### Listar Documentos em Cache

```bash
python run.py ocr-cache --list
```

Saida:
```
============================================================
  DOCUMENT ANALYZER - Cache OCR
============================================================

Documentos em Cache: 3

#    Arquivo                         Pags  Palavras    Tempo OCR  Idade
1    analise-licencas-software.pdf   47    12,345      45.3s      2h
2    contrato-aluguel.pdf            12    3,456       12.1s      1d
3    ata-reuniao.pdf                 8     2,100       8.5s       5d
```

### Ver Estatisticas

```bash
python run.py ocr-cache --stats
```

Saida:
```
Estatisticas do Cache OCR:

Metrica                  Valor
Status                   Habilitado
Documentos em Cache      3
Total de Paginas         67
Total de Palavras        17,901
Tamanho Original         15.20 MB
Tamanho do Cache         2.30 MB
Tempo Total Salvo        65.9s
Validade Maxima          720 horas
Diretorio                ./cache/ocr
```

### Informacoes de Documento Especifico

```bash
python run.py ocr-cache --info "analise-licencas-software.pdf"
```

### Remover Documento do Cache

```bash
# Por nome (parcial ou completo)
python run.py ocr-cache --remove "analise-licencas"

# Remove todos que contem "analise-licencas" no nome
```

### Limpar Entradas Expiradas

```bash
python run.py ocr-cache --cleanup
```

### Limpar Todo o Cache

```bash
python run.py ocr-cache --clear
```

---

## Uso no Q&A

O sistema Q&A usa o cache automaticamente:

```bash
# Primeira vez: executa OCR (lento)
python run.py qa documento.pdf -q "pergunta"
# Saida: "Carregando documento..."

# Segunda vez: usa cache (rapido)
python run.py qa documento.pdf -q "pergunta"
# Saida: "[CACHE] Usando texto em cache (OCR)"
```

### Desabilitar Cache para uma Consulta

```bash
python run.py qa documento.pdf -q "pergunta" --no-ocr-cache
```

---

## Configuracao

### config.yaml

```yaml
ocr_cache:
  enabled: true          # Habilitar/desabilitar cache
  dir: "./cache/ocr"     # Diretorio do cache
  max_age_hours: 720     # Validade em horas (30 dias)
```

### Desabilitar Completamente

```yaml
ocr_cache:
  enabled: false
```

---

## Estrutura dos Arquivos de Cache

### index.json

```json
{
  "a1b2c3d4e5f6g7h8...": {
    "file_name": "documento.pdf",
    "file_hash": "a1b2c3d4e5f6g7h8...",
    "file_size": 1234567,
    "num_pages": 47,
    "total_words": 12345,
    "extracted_at": "2024-01-15T10:30:00",
    "extraction_time_seconds": 45.3,
    "cache_file": "a1b2c3d4e5f6.json"
  }
}
```

### Arquivo de Documento (a1b2c3d4e5f6.json)

```json
{
  "file_name": "documento.pdf",
  "file_hash": "a1b2c3d4e5f6g7h8...",
  "pages": [
    {"number": 1, "text": "Texto da pagina 1..."},
    {"number": 2, "text": "Texto da pagina 2..."}
  ],
  "full_text": "Texto completo do documento...",
  "metadata": {}
}
```

---

## Casos de Uso

### 1. Analises Repetidas

Quando voce precisa fazer multiplas perguntas sobre o mesmo documento:

```bash
# Todas as consultas apos a primeira usam cache
python run.py qa doc.pdf -q "Quais as licencas?"
python run.py qa doc.pdf -q "Qual a mais critica?"
python run.py qa doc.pdf -q "Quais as recomendacoes?"
```

### 2. Ambiente Compartilhado

Se multiplos usuarios analisam os mesmos documentos, o cache compartilhado acelera para todos.

### 3. Testes e Desenvolvimento

Durante desenvolvimento de templates, evita re-extrair o mesmo documento:

```bash
# Testar diferentes templates sem re-OCR
python run.py qa doc.pdf -q "pergunta" --template template1
python run.py qa doc.pdf -q "pergunta" --template template2
```

---

## Boas Praticas

### Quando Limpar o Cache

- Apos atualizar o motor de OCR
- Se documentos foram corrompidos
- Para liberar espaco em disco
- Se extraicoes parecem incorretas

### Tamanho do Cache

O cache comprime bem:
- PDF de 15 MB → Cache de ~2 MB
- Economia de ~85% no armazenamento

### Backup

O cache nao e critico e pode ser recriado. Nao e necessario fazer backup da pasta `cache/ocr/`.

---

## Solucao de Problemas

### Cache nao esta sendo usado

1. Verifique se esta habilitado: `python run.py ocr-cache --stats`
2. Verifique se o documento mudou (hash diferente)
3. Verifique se o cache expirou

### Cache corrompido

```bash
# Limpar e deixar recriar
python run.py ocr-cache --clear
```

### Resposta diferente do esperado

O cache pode ter texto de versao anterior do documento:

```bash
# Remove documento especifico
python run.py ocr-cache --remove "documento.pdf"

# Re-processa
python run.py qa documento.pdf -q "pergunta"
```

### Erro de permissao

Verifique permissoes de escrita na pasta `cache/ocr/`.

