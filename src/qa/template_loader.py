"""
Carregador de Templates de Prompts.

Carrega templates de arquivos .txt para permitir que usuários
não-técnicos personalizem os prompts do sistema de Q&A.

Formato do arquivo de template:
    [INSTRUCAO_SISTEMA]
    Texto do prompt de sistema...
    
    [INSTRUCAO_USUARIO]
    Texto com {variaveis} para substituição...
    
    [FORMATO_RESPOSTA]
    Instruções de formato...
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Representa um template de prompt carregado de arquivo."""
    
    name: str
    file_path: Path
    system_instruction: str
    user_instruction: str
    response_format: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def format_system_prompt(self) -> str:
        """Retorna o prompt de sistema formatado."""
        return self.system_instruction.strip()
    
    def format_user_prompt(
        self,
        contexto: str,
        pergunta: str,
        documento: str = "",
        paginas: str = "",
        **kwargs
    ) -> str:
        """
        Formata o prompt do usuário com as variáveis fornecidas.
        
        Args:
            contexto: Trecho do documento encontrado
            pergunta: Pergunta do usuário
            documento: Nome do documento
            paginas: Páginas de referência
            **kwargs: Variáveis adicionais
        
        Returns:
            str: Prompt formatado
        """
        # Variáveis padrão
        variables = {
            "contexto": contexto,
            "pergunta": pergunta,
            "documento": documento,
            "paginas": paginas,
            "data": datetime.now().strftime("%d/%m/%Y"),
            "hora": datetime.now().strftime("%H:%M"),
        }
        
        # Adiciona variáveis extras
        variables.update(kwargs)
        
        # Formata o template
        result = self.user_instruction
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        # Adiciona formato de resposta se existir
        if self.response_format:
            result += f"\n\n{self.response_format}"
        
        return result.strip()
    
    def get_full_prompt(
        self,
        contexto: str,
        pergunta: str,
        documento: str = "",
        paginas: str = "",
        **kwargs
    ) -> Dict[str, str]:
        """
        Retorna o prompt completo com sistema e usuário.
        
        Returns:
            Dict com 'system' e 'user'
        """
        return {
            "system": self.format_system_prompt(),
            "user": self.format_user_prompt(
                contexto=contexto,
                pergunta=pergunta,
                documento=documento,
                paginas=paginas,
                **kwargs
            )
        }
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "file_path": str(self.file_path),
            "description": self.description,
            "has_system": bool(self.system_instruction),
            "has_user": bool(self.user_instruction),
            "has_format": bool(self.response_format),
        }


class TemplateLoader:
    """
    Carrega e gerencia templates de prompts de arquivos .txt.
    
    Os templates são carregados do diretório configurado e podem
    ser selecionados por nome ou detectados automaticamente.
    """
    
    # Marcadores de seção no arquivo
    SECTION_MARKERS = {
        "system": "[INSTRUCAO_SISTEMA]",
        "user": "[INSTRUCAO_USUARIO]",
        "format": "[FORMATO_RESPOSTA]",
    }
    
    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        default_template: str = "sistema_padrao"
    ):
        """
        Inicializa o carregador de templates.
        
        Args:
            templates_dir: Diretório dos templates
            default_template: Nome do template padrão
        """
        self.templates_dir = templates_dir or Path("./instructions/qa_templates")
        self.default_template = default_template
        self._templates: Dict[str, PromptTemplate] = {}
        self._loaded = False
    
    def load_all(self) -> int:
        """
        Carrega todos os templates do diretório.
        
        Returns:
            int: Número de templates carregados
        """
        if not self.templates_dir.exists():
            logger.warning(f"Diretório de templates não existe: {self.templates_dir}")
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            return 0
        
        count = 0
        for file_path in self.templates_dir.glob("*.txt"):
            # Ignora arquivos que começam com _
            if file_path.name.startswith("_"):
                continue
            
            try:
                template = self._load_template_file(file_path)
                if template:
                    self._templates[template.name] = template
                    count += 1
                    logger.debug(f"Template carregado: {template.name}")
            except Exception as e:
                logger.warning(f"Erro ao carregar template {file_path}: {e}")
        
        self._loaded = True
        logger.info(f"Carregados {count} templates de {self.templates_dir}")
        
        return count
    
    def _load_template_file(self, file_path: Path) -> Optional[PromptTemplate]:
        """
        Carrega um arquivo de template.
        
        Args:
            file_path: Caminho do arquivo
        
        Returns:
            PromptTemplate ou None se inválido
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Erro ao ler arquivo {file_path}: {e}")
            return None
        
        # Remove comentários (linhas começando com #)
        lines = []
        description_lines = []
        in_header = True
        
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                if in_header and stripped.startswith("# ") and not stripped.startswith("# =="):
                    # Coleta descrição do cabeçalho
                    desc = stripped[2:].strip()
                    if desc and not desc.startswith("="):
                        description_lines.append(desc)
                continue
            if stripped:
                in_header = False
            lines.append(line)
        
        content = "\n".join(lines)
        description = " ".join(description_lines[:3])  # Primeiras 3 linhas de descrição
        
        # Extrai seções
        sections = self._parse_sections(content)
        
        if not sections.get("user"):
            logger.warning(f"Template {file_path.name} não tem [INSTRUCAO_USUARIO]")
            return None
        
        return PromptTemplate(
            name=file_path.stem,  # Nome sem extensão
            file_path=file_path,
            system_instruction=sections.get("system", ""),
            user_instruction=sections.get("user", ""),
            response_format=sections.get("format", ""),
            description=description,
        )
    
    def _parse_sections(self, content: str) -> Dict[str, str]:
        """
        Extrai seções do conteúdo do template.
        
        Args:
            content: Conteúdo do arquivo
        
        Returns:
            Dict com seções extraídas
        """
        sections = {}
        
        # Encontra posições dos marcadores
        markers_pos = []
        for section_name, marker in self.SECTION_MARKERS.items():
            pos = content.find(marker)
            if pos >= 0:
                markers_pos.append((pos, section_name, marker))
        
        # Ordena por posição
        markers_pos.sort(key=lambda x: x[0])
        
        # Extrai conteúdo de cada seção
        for i, (pos, section_name, marker) in enumerate(markers_pos):
            start = pos + len(marker)
            
            # Fim é o próximo marcador ou fim do arquivo
            if i + 1 < len(markers_pos):
                end = markers_pos[i + 1][0]
            else:
                end = len(content)
            
            section_content = content[start:end].strip()
            sections[section_name] = section_content
        
        return sections
    
    def get_template(self, name: Optional[str] = None) -> PromptTemplate:
        """
        Obtém um template por nome.
        
        Args:
            name: Nome do template (sem extensão .txt)
                  Se None, retorna o template padrão
        
        Returns:
            PromptTemplate
        
        Raises:
            ValueError: Se template não encontrado
        """
        if not self._loaded:
            self.load_all()
        
        template_name = name or self.default_template
        
        if template_name not in self._templates:
            # Tenta carregar especificamente
            file_path = self.templates_dir / f"{template_name}.txt"
            if file_path.exists():
                template = self._load_template_file(file_path)
                if template:
                    self._templates[template_name] = template
                    return template
            
            # Se não encontrou, usa template padrão mínimo
            logger.warning(
                f"Template '{template_name}' não encontrado. "
                f"Usando template mínimo."
            )
            return self._get_fallback_template()
        
        return self._templates[template_name]
    
    def _get_fallback_template(self) -> PromptTemplate:
        """Retorna um template mínimo de fallback."""
        return PromptTemplate(
            name="_fallback",
            file_path=Path("_fallback"),
            system_instruction="""Você é um assistente que responde perguntas sobre documentos.
Responda apenas com base no contexto fornecido.
Se a informação não estiver no contexto, diga que não foi encontrada.
Responda em português brasileiro.""",
            user_instruction="""Documento: {documento}

Contexto encontrado (páginas {paginas}):
---
{contexto}
---

Pergunta: {pergunta}

Responda baseado apenas no contexto acima.""",
            response_format="",
            description="Template de fallback"
        )
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        Lista todos os templates disponíveis.
        
        Returns:
            Lista com informações dos templates
        """
        if not self._loaded:
            self.load_all()
        
        result = []
        for name, template in sorted(self._templates.items()):
            result.append({
                "name": name,
                "description": template.description,
                "file": template.file_path.name,
                "is_default": name == self.default_template,
            })
        
        return result
    
    def detect_template(self, text: str, rules: List[Dict[str, str]]) -> Optional[str]:
        """
        Detecta o melhor template baseado no conteúdo do documento.
        
        Args:
            text: Texto do documento (primeiras páginas)
            rules: Lista de regras {pattern: str, template: str}
        
        Returns:
            Nome do template ou None
        """
        text_lower = text.lower()
        
        for rule in rules:
            pattern = rule.get("pattern", "")
            template_name = rule.get("template", "")
            
            if not pattern or not template_name:
                continue
            
            try:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    if template_name in self._templates or \
                       (self.templates_dir / f"{template_name}.txt").exists():
                        logger.info(f"Template detectado automaticamente: {template_name}")
                        return template_name
            except re.error:
                logger.warning(f"Padrão regex inválido: {pattern}")
        
        return None
    
    def reload(self) -> int:
        """Recarrega todos os templates."""
        self._templates.clear()
        self._loaded = False
        return self.load_all()

