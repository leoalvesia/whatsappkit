#!/usr/bin/env python3
"""Testa funções utilitárias e filtros do whatsapp_manager.py.

Cobre:
- _resolve_phone_from_jid (LID vs JID normal, device suffix)
- _sanitize_sensitive (dados sensíveis: CPF, senha, saldo, token)
- _best_contact_name (prioridade bridge > log > fallback)
- _sanitize_classification_result (bloqueia parentesco do André como nickname)
- _owner_status_context_block (status ativo vs inativo, reveal_status)
- _detect_contact_query (detecção de perguntas sobre contatos)
- _normalize_text (normalização Unicode)

Uso:
    python3 test_utils_and_filters.py
"""

import sys
import os
import types
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN_PATH = Path("/opt/data/workspace/hermes-whatsapp-mixed/whatsapp_manager.py")


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


# ── Fixtures ──────────────────────────────────────────────────────────────────

STATUS_DORMINDO = {
    "description": "dormindo",
    "until_iso": "2099-01-01T08:00:00",
    "raw_text": "vou dormir",
}


# ── Testes ────────────────────────────────────────────────────────────────────

class TestResolvePhoneFromJid(unittest.TestCase):
    """_resolve_phone_from_jid — conversão de JID."""

    def test_jid_normal_retorna_igual(self):
        result = wm._resolve_phone_from_jid("558699997003@s.whatsapp.net")
        self.assertEqual(result, "558699997003@s.whatsapp.net")

    def test_remove_device_suffix(self):
        result = wm._resolve_phone_from_jid("558699997003@s.whatsapp.net:5")
        self.assertNotIn(":5", result)
        self.assertIn("558699997003", result)

    def test_jid_sem_dominio_assume_s_whatsapp(self):
        result = wm._resolve_phone_from_jid("558699997003")
        self.assertIn("s.whatsapp.net", result)

    def test_vazio_retorna_vazio(self):
        self.assertEqual(wm._resolve_phone_from_jid(""), "")

    def test_lid_sem_mapa_retorna_limpo(self):
        wm._lid_to_phone.clear()
        result = wm._resolve_phone_from_jid("abc123@lid")
        # Sem mapeamento, devolve o JID limpo
        self.assertIn("abc123", result)

    def test_lid_com_mapa_retorna_telefone(self):
        wm._lid_to_phone["abc123"] = "5511999999999"
        result = wm._resolve_phone_from_jid("abc123@lid")
        self.assertEqual(result, "5511999999999@s.whatsapp.net")
        del wm._lid_to_phone["abc123"]


class TestSanitizeSensitive(unittest.TestCase):
    """_sanitize_sensitive — filtra dados sensíveis."""

    def test_mensagem_normal_passa(self):
        result = wm._sanitize_sensitive("oi tudo bem?")
        self.assertEqual(result, "oi tudo bem?")

    def test_cpf_descartado(self):
        self.assertIsNone(wm._sanitize_sensitive("meu CPF é 123.456.789-09"))

    def test_cnpj_descartado(self):
        self.assertIsNone(wm._sanitize_sensitive("CNPJ: 12.345.678/0001-90"))

    def test_senha_descartada(self):
        self.assertIsNone(wm._sanitize_sensitive("minha senha é 1234"))

    def test_token_descartado(self):
        self.assertIsNone(wm._sanitize_sensitive("use este token para acessar"))

    def test_saldo_descartado(self):
        self.assertIsNone(wm._sanitize_sensitive("saldo R$ 1.500,00"))

    def test_cartao_longo_descartado(self):
        self.assertIsNone(wm._sanitize_sensitive("cartão 4111111111111111"))

    def test_cvv_descartado(self):
        self.assertIsNone(wm._sanitize_sensitive("cvv: 123"))

    def test_vazio_retorna_none(self):
        self.assertIsNone(wm._sanitize_sensitive(""))

    def test_mensagem_com_valor_baixo_passa(self):
        # "R$ 50" não deve ser descartado — limiar é R$ 1.000+
        result = wm._sanitize_sensitive("custou R$ 50 reais")
        self.assertIsNotNone(result)


class TestBestContactName(unittest.TestCase):
    """_best_contact_name — prioridade de fontes de nome."""

    def test_bridge_name_preferido(self):
        name, source = wm._best_contact_name("jid", "André Alencar", "db_name", "5511")
        self.assertEqual(name, "André Alencar")
        self.assertEqual(source, "bridge")

    def test_db_name_quando_bridge_generico(self):
        name, source = wm._best_contact_name("jid", None, "Rosemery", "5511")
        self.assertEqual(name, "Rosemery")
        self.assertEqual(source, "log")

    def test_fallback_quando_ambos_genericos(self):
        name, source = wm._best_contact_name("jid", None, None, "5511")
        self.assertIn("5511", name)
        self.assertEqual(source, "fallback")

    def test_jid_como_bridge_name_e_generico(self):
        name, source = wm._best_contact_name("jid", "5511@s.whatsapp.net", "Rosemery", "5511")
        self.assertEqual(name, "Rosemery")
        self.assertEqual(source, "log")

    def test_numero_puro_como_bridge_e_generico(self):
        name, source = wm._best_contact_name("jid", "+5511999999999", "Rosemery", "5511")
        self.assertEqual(name, "Rosemery")
        self.assertEqual(source, "log")


class TestSanitizeClassificationResult(unittest.TestCase):
    """_sanitize_classification_result — bloqueia parentesco do André como apelido."""

    def test_pai_como_nickname_zerado(self):
        res = wm._sanitize_classification_result({"nickname": "pai", "relationship": "Filho"})
        self.assertIsNone(res["nickname"])

    def test_mae_como_pet_name_zerado(self):
        res = wm._sanitize_classification_result({"pet_name": "mãe"})
        self.assertIsNone(res["pet_name"])

    def test_apelido_normal_mantido(self):
        res = wm._sanitize_classification_result({"nickname": "Zé", "relationship": "Amigo"})
        self.assertEqual(res["nickname"], "Zé")

    def test_dono_como_nickname_zerado(self):
        res = wm._sanitize_classification_result({"nickname": "dono"})
        self.assertIsNone(res["nickname"])

    def test_nao_dict_retorna_igual(self):
        res = wm._sanitize_classification_result("invalido")
        self.assertEqual(res, "invalido")

    def test_campos_outros_preservados(self):
        res = wm._sanitize_classification_result({
            "nickname": "pai",
            "relationship": "Filho",
            "tone": "carinhoso",
        })
        self.assertEqual(res["relationship"], "Filho")
        self.assertEqual(res["tone"], "carinhoso")


def _patch_globals(fn_name, fake):
    """Patcha uma função no __globals__ do exec namespace de forma segura."""
    globs = wm._owner_status_context_block.__globals__
    orig = globs[fn_name]
    globs[fn_name] = fake
    return globs, fn_name, orig


class TestOwnerStatusContextBlock(unittest.TestCase):
    """_owner_status_context_block — injeção de status no prompt."""

    def test_sem_status_retorna_vazio(self):
        globs, fn, orig = _patch_globals("_get_active_owner_status", lambda: None)
        try:
            result = wm._owner_status_context_block()
        finally:
            globs[fn] = orig
        self.assertEqual(result, "")

    def test_com_status_reveal_true_contem_descricao(self):
        globs, fn, orig = _patch_globals("_get_active_owner_status", lambda: STATUS_DORMINDO)
        try:
            result = wm._owner_status_context_block(reveal_status=True)
        finally:
            globs[fn] = orig
        self.assertIn("dormindo", result)
        self.assertIn("STATUS", result)

    def test_com_status_reveal_false_nao_revela_descricao(self):
        globs, fn, orig = _patch_globals("_get_active_owner_status", lambda: STATUS_DORMINDO)
        try:
            result = wm._owner_status_context_block(reveal_status=False)
        finally:
            globs[fn] = orig
        self.assertNotIn("dormindo", result)

    def test_until_iso_formatado_como_hora(self):
        globs, fn, orig = _patch_globals("_get_active_owner_status", lambda: STATUS_DORMINDO)
        try:
            result = wm._owner_status_context_block(reveal_status=True)
        finally:
            globs[fn] = orig
        # STATUS_DORMINDO.until_iso = "2099-01-01T08:00:00" → deve aparecer "08:00"
        self.assertIn("08:00", result)


class TestDetectContactQuery(unittest.TestCase):
    """_detect_contact_query — detecta perguntas sobre contatos na mensagem do owner."""

    def test_conversa_com_nome(self):
        result = wm._detect_contact_query("me mostra a conversa com Rosemery")
        self.assertIsNotNone(result)
        self.assertIn("rosemery", result.lower())

    def test_historico_de_nome(self):
        result = wm._detect_contact_query("histórico do Pedro")
        self.assertIsNotNone(result)

    def test_mensagem_generica_retorna_none(self):
        result = wm._detect_contact_query("qual é o tempo hoje?")
        self.assertIsNone(result)

    def test_stopword_nao_vira_contato(self):
        result = wm._detect_contact_query("conversa com ela")
        # "ela" é stopword — não deve retornar
        self.assertIsNone(result)


class TestNormalizeText(unittest.TestCase):
    """_normalize_text — remove acentos e lowercase."""

    def test_acento_removido(self):
        self.assertEqual(wm._normalize_text("André"), "andre")

    def test_cedilha_removida(self):
        self.assertEqual(wm._normalize_text("Ação"), "acao")

    def test_maiusculas_minusculas(self):
        self.assertEqual(wm._normalize_text("ROSEMERY"), "rosemery")

    def test_espaco_preservado(self):
        self.assertEqual(wm._normalize_text("São Paulo"), "sao paulo")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestResolvePhoneFromJid))
    suite.addTests(loader.loadTestsFromTestCase(TestSanitizeSensitive))
    suite.addTests(loader.loadTestsFromTestCase(TestBestContactName))
    suite.addTests(loader.loadTestsFromTestCase(TestSanitizeClassificationResult))
    suite.addTests(loader.loadTestsFromTestCase(TestOwnerStatusContextBlock))
    suite.addTests(loader.loadTestsFromTestCase(TestDetectContactQuery))
    suite.addTests(loader.loadTestsFromTestCase(TestNormalizeText))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
