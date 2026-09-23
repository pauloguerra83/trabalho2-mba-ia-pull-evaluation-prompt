"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

DICAS DE IMPLEMENTAÇÃO:

- O push é feito pelo cliente do LangSmith:

      from langsmith import Client
      from langchain_core.prompts import ChatPromptTemplate

      client = Client()
      prompt = ChatPromptTemplate.from_messages([
          ("system", system_prompt),
          ("user", user_prompt),
      ])
      url = client.push_prompt(
          f"{username}/bug_to_user_story_v2",
          object=prompt,
          is_public=True,
          description="...",
          tags=[...],
      )

- `username` vem de USERNAME_LANGSMITH_HUB no .env e precisa ser o seu handle
  do Hub. Se você ainda não tem um handle, veja as instruções no .env.example.

- A variável do template precisa ser {bug_report}, que é a chave de entrada
  usada no dataset de avaliação.

- Use `load_yaml` de utils.py para ler o arquivo .yml.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"
PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"
INPUT_VARIABLE = "bug_report"


def build_prompt_template(prompt_data: dict) -> ChatPromptTemplate:
    """Monta o ChatPromptTemplate (system + user) a partir dos dados do YAML."""
    return ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        prompt = build_prompt_template(prompt_data)

        techniques = prompt_data.get("techniques_applied", [])
        tags = list(dict.fromkeys(
            prompt_data.get("tags", [])
            + [prompt_data.get("version", "v2")]
            + [t.lower().replace(" ", "-") for t in techniques]
        ))
        description = (
            f"{prompt_data.get('description', '').strip()} "
            f"| Técnicas: {', '.join(techniques)}"
        )

        client = Client()
        url = client.push_prompt(
            prompt_name,
            object=prompt,
            is_public=True,
            description=description,
            tags=tags,
        )

        print(f"   ✓ Push realizado: {prompt_name}")
        print(f"   ✓ Tags: {', '.join(tags)}")
        print(f"   ✓ URL: {url}")
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Erro ao fazer push de '{prompt_name}': {error_msg}")
        if "Nothing to commit" in error_msg or "409" in error_msg:
            print("   ℹ️  O conteúdo é idêntico à última versão publicada. Altere o YAML antes de refazer o push.")
        else:
            print("   Verifique LANGSMITH_API_KEY e se USERNAME_LANGSMITH_HUB é o seu handle público do Hub.")
        return False


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    _, errors = validate_prompt_structure(prompt_data)

    user_prompt = (prompt_data.get("user_prompt") or "").strip()
    if not user_prompt:
        errors.append("user_prompt está vazio")

    try:
        variables = set(build_prompt_template(prompt_data).input_variables)
    except Exception as e:
        errors.append(f"Template inválido: {e}")
        variables = set()

    if variables and variables != {INPUT_VARIABLE}:
        errors.append(
            f"O template deve usar apenas a variável {{{INPUT_VARIABLE}}}, encontradas: {sorted(variables)}"
        )

    if f"{{{INPUT_VARIABLE}}}" in prompt_data.get("system_prompt", ""):
        errors.append(f"{{{INPUT_VARIABLE}}} deve aparecer apenas no user_prompt, não no system_prompt")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_FILE))
    if not data or PROMPT_KEY not in data:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {PROMPT_FILE}")
        return 1

    prompt_data = data[PROMPT_KEY]

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("   ✓ Prompt validado")

    username = os.getenv("USERNAME_LANGSMITH_HUB")
    prompt_name = f"{username}/{PROMPT_KEY}"

    if not push_prompt_to_langsmith(prompt_name, prompt_data):
        return 1

    print("\n✅ Push concluído! Próximo passo: python src/evaluate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
