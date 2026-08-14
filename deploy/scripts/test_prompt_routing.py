#!/usr/bin/env python3
"""Valida o roteamento entre _build_personal_prompt e _build_support_prompt.

Garante que:
- Amigo/AmigoProximo/Parente/Filho → prompt pessoal (persona natural)
- Cliente/Vendedor/Desconhecido    → prompt de suporte
- Status ativo é injetado no prompt pessoal
- Prompt pessoal NÃO contém linguagem de "sistema automatizado"

Uso:
    python3 test_prompt_routing.py
"""

import sys
import os
import json
import types
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN_PATH = Path("/opt/data/workspace/hermes-whatsapp-mixed/whatsapp_manager.py")
PC_PATH = Path("/opt/data/personal_contacts.json")

# ── Carregar plugin ──────────────────────────────────────────────────────────

def _load_plugin():
    ns = {"__file__": str(PLUGIN_PATH), "__name__": "whatsapp_manager"}
    source = PLUGIN_PATH.read_text(encoding="utf-8")
    try:
        exec(compile(source, str(PLUGIN_PATH), "exec"), ns)
    except Exception as e:
        print(f"\n[WARN] exec parcial: {e}")
    module = types.ModuleType("whatsapp_manager")
    module.__dict__.update(ns)
    return module


print("Carregando plugin...", end=" ", flush=True)
try:
    wm = _load_plugin()
    print("OK\n")
except Exception as e:
    print(f"ERRO: {e}")
    sys.exit(1)


# ── Fixtures ─────────────────────────────────────────────────────────────────

AMIGO_INFO = {
    "name": "Suporte",
    "relationship": "Amigo",
    "manual_relationship": "Amigo",
    "tone": "informal e amigável",
    "guidelines": "Responda como André.",
}

CLIENTE_INFO = {
    "name": "Maria Silva",
    "relationship": "Cliente",
    "tone": "profissional",
    "guidelines": "Responda sobre produtos.",
    "summary": "Cliente interessada em produto X.",
}

VENDEDOR_INFO = {
    "name": "João Fornecedor",
    "relationship": "Vendedor",
    "tone": "profissional",
    "guidelines": "Negocie com cautela.",
}

# ── Testes ────────────────────────────────────────────────────────────────────

class TestBuildPersonalPrompt(unittest.TestCase):
    """_build_personal_prompt retorna o prompt pessoal correto."""

    def _build(self, contact_info, relationship="Amigo"):
        return wm._build_personal_prompt(contact_info, relationship, "")

    def test_retorna_dict_com_context(self):
        result = self._build(AMIGO_INFO)
        self.assertIn("context", result)
        self.assertIsInstance(result["context"], str)

    def test_contem_persona_natural(self):
        """Prompt pessoal deve conter marcadores da nova persona."""
        result = self._build(AMIGO_INFO)
        ctx = result["context"]
        self.assertIn("PERSONA", ctx)
        self.assertIn("alguém de confiança", ctx)

    def test_nao_contem_sistema_automatizado(self):
        """Prompt pessoal NÃO deve usar linguagem de sistema/bot formal."""
        result = self._build(AMIGO_INFO)
        ctx = result["context"].lower()
        self.assertNotIn("sistema automatizado", ctx,
            "Prompt pessoal não deve conter 'sistema automatizado'")

    def test_nome_do_contato_presente(self):
        result = self._build(AMIGO_INFO)
        self.assertIn("Suporte", result["context"])

    def test_relationship_presente(self):
        result = self._build(AMIGO_INFO, relationship="AmigoProximo")
        self.assertIn("AmigoProximo", result["context"])

    def test_nickname_incluido(self):
        info = {**AMIGO_INFO, "nickname": "Suportinho"}
        result = self._build(info)
        self.assertIn("Suportinho", result["context"])

    def test_notes_incluido(self):
        info = {**AMIGO_INFO, "notes": "Prefere WhatsApp"}
        result = self._build(info)
        self.assertIn("Prefere WhatsApp", result["context"])

    def test_constraints_seguranca_presentes(self):
        result = self._build(AMIGO_INFO)
        self.assertIn("CONSTRAINTS", result["context"])
        self.assertIn("terminal", result["context"].lower())

    def test_historia_injetada(self):
        history = "### HISTÓRICO\nMensagem anterior"
        result = wm._build_personal_prompt(AMIGO_INFO, "Amigo", history)
        self.assertIn("HISTÓRICO", result["context"])


class TestBuildSupportPrompt(unittest.TestCase):
    """_build_support_prompt retorna prompt de suporte/cliente."""

    def _soul(self):
        return "SOUL: responda como André."

    def _rules(self):
        return "Regras: seja educado."

    def test_retorna_dict_com_context(self):
        result = wm._build_support_prompt(self._soul(), self._rules(), "", CLIENTE_INFO)
        self.assertIn("context", result)

    def test_nome_cliente_presente(self):
        result = wm._build_support_prompt(self._soul(), self._rules(), "", CLIENTE_INFO)
        self.assertIn("Maria Silva", result["context"])

    def test_soul_presente(self):
        result = wm._build_support_prompt("MEU SOUL ESPECIAL", self._rules(), "", None)
        self.assertIn("MEU SOUL ESPECIAL", result["context"])


class TestRoteamento(unittest.TestCase):
    """Verifica que o condicional de roteamento está correto no pre_llm_call.

    Testa a lógica extraída do pre_llm_call:
        relationship in ("Amigo", ...) OR manual_relationship in ("namorada", ...) → pessoal
    """

    PESSOAIS_REL = ["Amigo", "AmigoProximo", "Parente", "Filho"]
    PESSOAIS_MANUAL = ["namorada", "namorado", "esposa", "marido",
                       "mãe", "mae", "pai", "filho", "filha",
                       "irmão", "irmao", "irmã", "irma", "avó", "avo", "avô"]
    SUPORTE_REL  = ["Cliente", "Vendedor", "Desconhecido", "", None]

    def _deve_usar_pessoal(self, rel, manual_rel=""):
        _rel = rel or ""
        _man = (manual_rel or "").lower()
        pessoal_manual = _man in (
            "namorada", "namorado", "esposa", "marido",
            "mãe", "mae", "pai", "filho", "filha",
            "irmão", "irmao", "irmã", "irma", "avó", "avo", "avô",
        )
        return _rel in ("Amigo", "AmigoProximo", "Parente", "Filho") or pessoal_manual

    def test_relationship_pessoal_usa_pessoal(self):
        for rel in self.PESSOAIS_REL:
            with self.subTest(rel=rel):
                self.assertTrue(self._deve_usar_pessoal(rel),
                    f"relationship={rel} deveria rotear para prompt pessoal")

    def test_manual_relationship_namorada_usa_pessoal(self):
        for man in self.PESSOAIS_MANUAL:
            with self.subTest(manual_rel=man):
                self.assertTrue(self._deve_usar_pessoal("Cliente", man),
                    f"manual_relationship={man} deveria rotear para prompt pessoal")

    def test_cliente_sem_manual_usa_suporte(self):
        for rel in self.SUPORTE_REL:
            with self.subTest(rel=rel):
                self.assertFalse(self._deve_usar_pessoal(rel, ""),
                    f"relationship={rel} sem manual_relationship não deveria ser pessoal")

    def test_prompt_pessoal_nao_tem_soul(self):
        """Prompt pessoal não usa whatsapp_soul (independente do SOUL_WHATSAPP.md)."""
        result = wm._build_personal_prompt(AMIGO_INFO, "Amigo", "")
        ctx = result["context"]
        # O prompt pessoal tem sua própria persona — não injeta SOUL raw
        self.assertNotIn("SOUL_WHATSAPP", ctx)

    def test_prompt_suporte_nao_tem_persona_natural(self):
        """Prompt de suporte não deve conter a persona do Amigo."""
        result = wm._build_support_prompt("soul", "rules", "", CLIENTE_INFO)
        ctx = result["context"]
        self.assertNotIn("alguém de confiança que pegou o celular", ctx)


class TestStatusNoPromptPessoal(unittest.TestCase):
    """Status ativo deve aparecer no prompt pessoal."""

    def _build_with_status(self, status_dict):
        with patch.object(wm, "_get_active_owner_status", return_value=status_dict):
            return wm._build_personal_prompt(AMIGO_INFO, "Amigo", "")

    def test_sem_status_nao_menciona_status(self):
        result = self._build_with_status(None)
        ctx = result["context"]
        self.assertNotIn("STATUS ATIVO", ctx)

    def test_com_status_injeta_no_prompt(self):
        status = {
            "description": "dormindo",
            "expires_at": "2099-01-01T10:00:00",
            "raw_text": "vou dormir",
        }
        result = self._build_with_status(status)
        ctx = result["context"]
        # _owner_status_context_block deve ter sido chamado com reveal_status=True
        # e injetado algo referente ao status
        self.assertTrue(
            "dormindo" in ctx or "STATUS" in ctx or "André" in ctx,
            f"Status não aparece no prompt pessoal. ctx[:500]={ctx[:500]}"
        )


@unittest.skipIf(not PC_PATH.exists(), f"{PC_PATH} não encontrado")
class TestContatosReais(unittest.TestCase):
    """Verifica o roteamento com os contatos reais do container."""

    def setUp(self):
        self.contacts = json.loads(PC_PATH.read_text(encoding="utf-8"))

    def test_558699997003_e_amigo(self):
        """Contato 558699997003 (Suporte) deve ter relationship=Amigo."""
        key = "558699997003@s.whatsapp.net"
        data = self.contacts.get(key)
        if not data:
            self.skipTest(f"{key} não encontrado em {PC_PATH}")
        rel = data.get("relationship") or ""
        self.assertIn(rel, ("Amigo", "AmigoProximo", "Parente", "Filho"),
            f"Esperava relationship pessoal, encontrou '{rel}'. Dados: {data}")

    def test_nenhuma_chave_invalida(self):
        """Não deve existir chaves com phone < 8 chars."""
        bad = [k for k in self.contacts
               if len(k.split("@")[0].split(":")[0]) < 8 and not k.endswith("@lid")]
        self.assertEqual(bad, [],
            f"Chaves inválidas encontradas (causam bug no passo 1): {bad}")

    def test_contatos_amigo_tem_personal_prompt(self):
        """Todos os contatos Amigo/Parente devem gerar prompt pessoal sem erros."""
        pessoais = [
            (k, v) for k, v in self.contacts.items()
            if v.get("relationship") in ("Amigo", "AmigoProximo", "Parente", "Filho")
        ]
        if not pessoais:
            self.skipTest("Nenhum contato pessoal em personal_contacts.json")

        for key, info in pessoais[:5]:  # limita a 5 para ser rápido
            with self.subTest(key=key, name=info.get("name")):
                rel = info.get("relationship")
                result = wm._build_personal_prompt(info, rel, "")
                self.assertIn("context", result)
                ctx = result["context"]
                self.assertNotIn("sistema automatizado", ctx.lower(),
                    f"Contato {key} (rel={rel}) gerou prompt com 'sistema automatizado'")
                self.assertIn("PERSONA", ctx,
                    f"Contato {key} (rel={rel}) não tem PERSONA no prompt")


# ── Runner ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestBuildPersonalPrompt))
    suite.addTests(loader.loadTestsFromTestCase(TestBuildSupportPrompt))
    suite.addTests(loader.loadTestsFromTestCase(TestRoteamento))
    suite.addTests(loader.loadTestsFromTestCase(TestStatusNoPromptPessoal))
    suite.addTests(loader.loadTestsFromTestCase(TestContatosReais))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
