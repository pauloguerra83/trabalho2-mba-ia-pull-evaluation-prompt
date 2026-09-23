"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

DICAS DE IMPLEMENTAÇÃO:

- O pull é feito pelo cliente do LangSmith:

      from langsmith import Client
      client = Client()
      prompt = client.pull_prompt(
          "leonanluppi/bug_to_user_story_v1",
          dangerously_pull_public_prompt=True,
      )

- O parâmetro `dangerously_pull_public_prompt=True` é obrigatório sempre que o
  identificador tem dono explícito ("owner/nome"). O LangSmith bloqueia esse pull
  por padrão porque um prompt do Hub é um objeto LangChain serializado, que pode
  vir de terceiros. Aqui o prompt é o do desafio, então o risco é conhecido.

- O retorno é um ChatPromptTemplate. Para extrair o conteúdo das mensagens,
  use a serialização nativa do LangChain (`prompt.messages`, e o atributo
  `.prompt.template` de cada mensagem).

- Use `save_yaml` de utils.py para gravar o resultado no arquivo .yml.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
PROMPT_KEY = "bug_to_user_story_v1"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"

# Mapeia o tipo da mensagem do ChatPromptTemplate para o campo do YAML
MESSAGE_FIELDS = {
    "SystemMessagePromptTemplate": "system_prompt",
    "HumanMessagePromptTemplate": "user_prompt",
}


def pull_prompts_from_langsmith():
    """
    Faz pull do prompt semente do LangSmith Hub e converte para o formato YAML.

    Returns:
        Dicionário no formato {PROMPT_KEY: {...}} ou None em caso de erro
    """
    try:
        client = Client()
        print(f"   Puxando prompt do LangSmith Hub: {SOURCE_PROMPT}")
        prompt = client.pull_prompt(SOURCE_PROMPT, dangerously_pull_public_prompt=True)
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt '{SOURCE_PROMPT}': {e}")
        return None

    prompt_data = {
        "description": "Prompt para converter relatos de bugs em User Stories",
        "system_prompt": "",
        "user_prompt": "",
    }

    for message in prompt.messages:
        field = MESSAGE_FIELDS.get(type(message).__name__)
        template = getattr(getattr(message, "prompt", None), "template", None)
        if field and template is not None:
            prompt_data[field] = template

    prompt_data.update({
        "input_variables": list(prompt.input_variables),
        "source": SOURCE_PROMPT,
        "version": "v1",
        "tags": ["bug-analysis", "user-story", "product-management"],
    })

    print(f"   ✓ {len(prompt.messages)} mensagens extraídas (variáveis: {prompt.input_variables})")
    return {PROMPT_KEY: prompt_data}


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    data = pull_prompts_from_langsmith()
    if not data:
        return 1

    if not save_yaml(data, str(OUTPUT_FILE)):
        return 1

    print(f"   ✓ Prompt salvo em: {OUTPUT_FILE}")
    print("\n✅ Pull concluído com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
