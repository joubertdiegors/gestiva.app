"""
Fill empty msgstr in locale/pt_BR/LC_MESSAGES/django.po and strip bad fuzzy matches.

Typical workflow (repo root, venv active):

  venv\\Scripts\\python manage.py makemessages -l pt_BR --no-location --ignore=venv
  venv\\Scripts\\python scripts\\complete_django_po.py
  venv\\Scripts\\python manage.py compilemessages -l pt_BR

Requires: pip install -r requirements-dev.txt

Uses Google Translate (deep-translator) for English msgids; Portuguese-looking
msgids are normalized to pt-BR spelling. Review django.po for domain terms.
"""
from __future__ import annotations

import re
import sys
import time
from datetime import datetime
from pathlib import Path

import polib

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("pip install deep-translator", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
PO_PATH = ROOT / "locale" / "pt_BR" / "LC_MESSAGES" / "django.po"

PT_DIACRITICS = re.compile(r"[áàâãéêíóôõúçñÁÀÂÃÉÊÍÓÔÕÚÇÑ]")

# Hand-tuned overrides after auto-translate (pt-BR wording / domain terms)
OVERRIDES: dict[str, str] = {
    "Save": "Salvar",
    "Delete": "Excluir",
    "Search": "Pesquisar",
    "Fleet": "Frota",
    "Planning": "Planejamento",
    "Timesheets": "Folhas de horas",
    "Suppliers": "Fornecedores",
    "Procurement": "Compras",
    "Back": "Voltar",
    "View": "Ver",
    "Petrol": "Gasolina",
    "Tyre": "Pneu",
    "Car Wash": "Lavagem",
    "Fine": "Multa",
    "Fines": "Multas",
    "Payroll": "Folha de pagamento",
    "Documents": "Documentos",
    "Workshop": "Oficina",
    "Liters": "Litros",
    "Full Tank": "Tanque cheio",
    "User": "Usuário",
    "Users": "Usuários",
    "Group": "Grupo",
    "Color": "Cor",
    "Orange": "Laranja",
    "Green": "Verde",
    "Amber": "Âmbar",
    "Red": "Vermelho",
    "Gray": "Cinza",
    "Access profile": "Perfil de acesso",
    "Access profiles": "Perfis de acesso",
}


def looks_portuguese(text: str) -> bool:
    if PT_DIACRITICS.search(text):
        return True
    markers = (
        "ções",
        "ção",
        "ões",
        "orçamento",
        "obrigatório",
        "obrigatorio",
        "Nenhum",
        "Nenhuma",
        "Excluir",
        "Eliminar",
        "Guardar",
        "Seleccione",
        "Selecione",
        "morada",
        "Morada",
        "contacto",
        "Contacto",
        "Utilizador",
        "utilizador",
        "projecto",
        "Projecto",
        "ligação",
        "Ligação",
        "actualiz",
        "Actualiz",
        "empresa",
        "Empresa",
        "«",
        "»",
        "…",
    )
    return any(m in text for m in markers)


def normalize_pt_br(text: str) -> str:
    s = text
    s = s.replace("Seleccione", "Selecione").replace("actualiza", "atualiza")
    s = s.replace("Actualiza", "Atualiza").replace("Actualizado", "Atualizado")
    s = s.replace("projecto", "projeto").replace("Projecto", "Projeto")
    s = s.replace("Utilizador", "Usuário").replace("utilizador", "usuário")
    s = s.replace("contacto", "contato").replace("Contacto", "Contato")
    s = s.replace("Morada", "Endereço").replace("morada", "endereço")
    s = s.replace("Ligação", "Conexão").replace("ligação", "conexão")
    s = s.replace("Eliminar", "Excluir").replace("eliminar", "excluir")
    s = s.replace("Guardar", "Salvar").replace("guardar", "salvar")
    s = s.replace("activo", "ativo").replace("Activo", "Ativo").replace("activa", "ativa")
    s = s.replace("effectivo", "efetivo").replace("Effectivo", "Efetivo")
    s = s.replace("  ", " ")
    return s


def main() -> None:
    po = polib.pofile(str(PO_PATH))
    translator = GoogleTranslator(source="en", target="pt")

    cleared = 0
    for entry in po:
        if "fuzzy" in entry.flags:
            entry.msgstr = ""
            entry.flags.remove("fuzzy")
            cleared += 1

    to_translate: list[tuple[polib.POEntry, str]] = []
    for entry in po:
        if entry.msgid == "":
            continue
        if entry.msgid_plural:
            continue
        msg = entry.msgid
        cur = (entry.msgstr or "").strip()
        if cur:
            continue
        to_translate.append((entry, msg))

    print(f"Cleared {cleared} fuzzy entries; filling {len(to_translate)} empty msgstr…")

    for i, (entry, msg) in enumerate(to_translate):
        if msg in OVERRIDES:
            entry.msgstr = OVERRIDES[msg]
            continue
        if looks_portuguese(msg):
            entry.msgstr = normalize_pt_br(msg)
            continue
        # English or mixed: machine translate
        try:
            out = translator.translate(msg)
            time.sleep(0.12)
        except Exception as exc:  # noqa: BLE001
            print(f"WARN [{i}] {msg[:60]}… -> {exc}")
            out = msg
        entry.msgstr = normalize_pt_br(out) if out else msg

        if (i + 1) % 50 == 0:
            print(f"  … {i + 1}/{len(to_translate)}")

    po.metadata["PO-Revision-Date"] = datetime.now().strftime("%Y-%m-%d %H:%M%z")
    po.save()
    print(f"Saved {PO_PATH}")


if __name__ == "__main__":
    main()
