"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt_data():
    data = load_prompts(PROMPT_FILE)
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada em {PROMPT_FILE.name}"
    return data[PROMPT_KEY]


@pytest.fixture(scope="module")
def system_prompt(prompt_data):
    return prompt_data.get("system_prompt", "")


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt_data
        assert isinstance(prompt_data["system_prompt"], str)
        assert prompt_data["system_prompt"].strip()

    def test_prompt_has_role_definition(self, system_prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert "Você é um" in system_prompt
        assert "Product Manager" in system_prompt

    def test_prompt_mentions_format(self, system_prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        assert "User Story" in system_prompt
        assert "FORMATO DE SAÍDA" in system_prompt
        for keyword in ["Como um", "eu quero", "para que"]:
            assert keyword in system_prompt, f"Template de User Story sem '{keyword}'"
        for keyword in ["Critérios de Aceitação", "Dado que", "Quando", "Então"]:
            assert keyword in system_prompt, f"Critérios de aceitação sem '{keyword}'"

    def test_prompt_has_few_shot_examples(self, system_prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        examples = re.findall(r"^#+\s*Exemplo \d+", system_prompt, flags=re.MULTILINE)
        assert len(examples) >= 2, "Few-shot exige pelo menos 2 exemplos"
        assert system_prompt.count("Entrada:") >= len(examples)
        assert system_prompt.count("Saída:") >= len(examples)

    def test_prompt_no_todos(self, prompt_data):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        for field, value in prompt_data.items():
            if isinstance(value, str):
                assert "[TODO]" not in value, f"Campo '{field}' contém [TODO]"
                assert "TODO" not in value, f"Campo '{field}' contém TODO"

    def test_minimum_techniques(self, prompt_data):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt_data.get("techniques_applied", [])
        assert isinstance(techniques, list)
        assert len(techniques) >= 2
        assert "Few-shot Learning" in techniques, "Few-shot Learning é obrigatório"

    def test_prompt_structure_is_valid(self, prompt_data):
        """Valida o prompt com a mesma função usada antes do push."""
        is_valid, errors = validate_prompt_structure(prompt_data)
        assert is_valid, errors

    def test_bug_report_only_in_user_prompt(self, prompt_data):
        """A variável {bug_report} deve estar somente no user_prompt (erro da v1)."""
        assert "{bug_report}" in prompt_data["user_prompt"]
        assert "{bug_report}" not in prompt_data["system_prompt"]

    def test_template_renders(self, prompt_data):
        """O template deve montar sem erro e ter apenas a variável bug_report."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system_prompt"]),
            ("user", prompt_data["user_prompt"]),
        ])
        assert set(prompt.input_variables) == {"bug_report"}
        messages = prompt.format_messages(bug_report="Botão X não funciona.")
        assert "Botão X não funciona." in messages[1].content

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])