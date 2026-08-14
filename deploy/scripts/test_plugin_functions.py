#!/usr/bin/env python3
"""Valida as funções reais do whatsapp_manager.py no servidor.

Importa o plugin com mocks mínimos e chama as funções diretamente.
Não reimplementa lógica — testa o código que está em produção.

Uso:
    python3 test_plugin_functions.py           # suite completa
    python3 test_plugin_functions.py --llm     # inclui testes de LLM (mais lento)
    python3 test_plugin_functions.py --quick   # só funções puras (sem I/O)
"""

import sys
import os
import re
import json
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PLUGIN_PATH = Path("/opt/data/workspace/hermes-whatsapp-mixed/whatsapp_manager.py")
PC_PATH = Path("/opt/data/personal_contacts.json")
HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data/.hermes")

RUN_LLM = "--llm" in sys.argv
RUN_QUICK = "--quick" in sys.argv

# ── Carregar plugin com mocks mínimos ──────────────────────────────────────────

def _load_plugin():
    """Executa whatsapp_manager.py num namespace isolado e retorna como módulo.

    PluginConfig já lê API keys do ambiente via @property — não é necessário injetar nada.
    """
    # Namespace com __builtins__ e __file__ para o exec funcionar
    ns = {"__file__": str(PLUGIN_PATH), "__name__": "whatsapp_manager"}

    source = PLUGIN_PATH.read_text(encoding="utf-8")
    try:
        exec(compile(source, str(PLUGIN_PATH), "exec"), ns)
    except Exception as e:
        print(f"\n[WARN] exec parcial: {e}")

    # Criar módulo a partir do namespace
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


# ── Suite de testes ────────────────────────────────────────────────────────────

class TestNormalizacao(unittest.TestCase):
    """Funções puras de normalização — sem I/O."""

    def test_normalize_br_com_nono_digito(self):
        fn = wm._normalize_brazilian_phone
        self.assertEqual(fn("5511987654321"), fn("551187654321"))

    def test_normalize_br_sem_nono_digito(self):
        fn = wm._normalize_brazilian_phone
        result = fn("551187654321")
        self.assertIn(result, ("551187654321", "5511987654321"))

    def test_normalize_br_idempotente(self):
        fn = wm._normalize_brazilian_phone
        n = "5511987654321"
        self.assertEqual(fn(fn(n)), fn(n))

    def test_normalize_text(self):
        fn = wm._normalize_text
        self.assertEqual(fn("André"), "andre")
        self.assertEqual(fn("São Paulo"), "sao paulo")
        self.assertEqual(fn("ROSEMERY"), "rosemery")


@unittest.skipIf(not PC_PATH.exists(), f"{PC_PATH} não encontrado")
class TestBuscaContatos(unittest.TestCase):
    """Busca em personal_contacts.json real."""

    def setUp(self):
        self.contacts = json.loads(PC_PATH.read_text(encoding="utf-8"))

    def test_busca_por_numero_existente(self):
        """Busca por número de contato que está em personal_contacts.json."""
        # Pega o primeiro contato não-owner com número válido
        contacts = self.contacts
        owner_digits = re.sub(r"\D", "", wm.config.whatsapp_owner_number or "")
        candidate_key = None
        for key, data in contacts.items():
            phone = key.split("@")[0].split(":")[0]
            if owner_digits and phone == owner_digits:
                continue
            if len(phone) >= 10 and data.get("name"):
                candidate_key = key
                break
        if not candidate_key:
            self.skipTest("Nenhum contato com número válido encontrado")
        phone = candidate_key.split("@")[0].split(":")[0]
        result = wm._update_contact_fields(phone, {})
        self.assertNotIn("não encontrado", result.lower(),
            f"Contato {phone} não encontrado por número: {result}")

    def test_rosemery_por_nome(self):
        """Busca por nome Rosemery — pula se não estiver nos contatos."""
        rosemery_exists = any(
            (v.get("name") or "").lower() == "rosemery"
            for v in self.contacts.values()
        )
        if not rosemery_exists:
            self.skipTest("Rosemery não está em personal_contacts.json neste ambiente")
        result = wm._update_contact_fields("Rosemery", {})
        self.assertNotIn("não encontrado", result.lower(),
            f"Rosemery não encontrada por nome: {result}")

    def test_suporte_nao_encontra_rosemery(self):
        """Busca por 'Suporte' não deve retornar o contato Rosemery."""
        candidates = wm._find_contact_matches("Suporte")
        keys = [k for k, _, _ in candidates]
        self.assertNotIn("5511996472188@s.whatsapp.net", keys,
            "Busca por 'Suporte' retornou Rosemery incorretamente")

    def test_numero_formatado_com_espacos(self):
        """Número com espaços e hífens deve normalizar corretamente."""
        fn = wm._normalize_brazilian_phone
        n1 = fn("".join(c for c in "+55 11 9964-72188" if c.isdigit()))
        n2 = fn("5511996472188")
        self.assertEqual(n1, n2, f"Normalização falhou: {n1} != {n2}")

    def test_sem_falso_positivo_por_score_zero(self):
        """Nome sem palavras em comum não deve retornar candidatos."""
        candidates = wm._find_contact_matches("XYZ_Inexistente_999")
        self.assertEqual(candidates, [],
            f"Esperava lista vazia mas encontrou: {candidates}")

    def test_ambiguidade_detectada(self):
        """_find_contact_matches deve retornar lista."""
        candidates = wm._find_contact_matches("Rosemery")
        # Pode ter 0 ou mais — só valida que é lista de tuplas
        for item in candidates:
            self.assertEqual(len(item), 3, f"Tupla inválida: {item}")


@unittest.skipIf(not RUN_LLM, "Pule com --llm para executar testes de LLM")
class TestLLM(unittest.TestCase):
    """Chamadas reais ao LLM — requer API key."""

    def _get_identifier(self, result: dict) -> str:
        """Retorna contact_identifier ou contact_name (compatibilidade)."""
        return (result.get("contact_identifier") or result.get("contact_name") or "").lower()

    def test_classify_identifier_por_nome(self):
        """Mensagem sem número → identifier deve ser o nome atual do contato."""
        result = wm._classify_owner_intent("coloque a Mayra como namorada")
        self.assertTrue(result.get("is_update"), f"Esperava is_update=True: {result}")
        self.assertIn("mayra", self._get_identifier(result),
            f"Identifier deveria conter 'mayra': {result}")

    def test_classify_identifier_por_numero(self):
        """Mensagem com número → identifier deve ser o número, não o nome futuro."""
        result = wm._classify_owner_intent(
            "coloque o número 558699997003, o nome dele é Suporte, como amigo"
        )
        self.assertTrue(result.get("is_update"), f"Esperava is_update=True: {result}")
        identifier = self._get_identifier(result)
        self.assertIn("558699997003", identifier,
            f"Identifier deveria ser o número, não o nome futuro. Resultado: {result}")
        self.assertNotIn("suporte", identifier,
            f"Identifier não deve ser o nome futuro 'Suporte'. Resultado: {result}")

    def test_extract_fields_renomear_com_numero(self):
        """Quando há número, name extraído é o nome futuro (não o identifier)."""
        result = wm._extract_update_fields_via_llm(
            "558699997003",
            "coloque o número 558699997003, o nome dele é Suporte, como amigo"
        )
        self.assertIn("name", result, f"Campo 'name' não extraído: {result}")
        self.assertIn("suporte", result.get("name", "").lower(),
            f"name deveria ser 'Suporte': {result}")
        self.assertIn("relationship", result, f"Campo 'relationship' não extraído: {result}")

    def test_classify_intent_status(self):
        result = wm._classify_owner_intent("vou estar no futebol até as 21h")
        self.assertTrue(result.get("is_status"), f"Esperava is_status=True: {result}")
        self.assertFalse(result.get("is_clear"), f"Não deveria ser clear: {result}")

    def test_classify_intent_status_clear(self):
        result = wm._classify_owner_intent("já voltei")
        self.assertTrue(result.get("is_status"), f"Esperava is_status=True: {result}")
        self.assertTrue(result.get("is_clear"), f"Esperava is_clear=True: {result}")

    def test_classify_intent_other(self):
        result = wm._classify_owner_intent("qual o saldo da conta?")
        self.assertFalse(result.get("is_update"), f"Não deveria ser update: {result}")
        self.assertFalse(result.get("is_status"), f"Não deveria ser status: {result}")

    def test_classify_intent_nao_update_pergunta(self):
        result = wm._classify_owner_intent("o que você acha do Pedro?")
        self.assertFalse(result.get("is_update"), f"Não deveria ser update: {result}")

    def test_extract_fields_notes(self):
        result = wm._extract_update_fields_via_llm("Juan", "coloque uma observação no Juan: ele prefere WhatsApp")
        self.assertIn("notes", result, f"Campo 'notes' não extraído: {result}")

    def test_extract_fields_nickname(self):
        result = wm._extract_update_fields_via_llm("Pedro", "o apelido do Pedro é Pedrinho")
        self.assertIn("nickname", result, f"Campo 'nickname' não extraído: {result}")
        self.assertIn("pedrinho", result.get("nickname", "").lower())

    def test_extract_fields_relationship(self):
        result = wm._extract_update_fields_via_llm("Mayra", "coloque a Mayra como namorada")
        self.assertIn("relationship", result, f"Campo 'relationship' não extraído: {result}")
        self.assertEqual(result.get("relationship"), "AmigoProximo")
        self.assertIn("manual_relationship", result)

    def test_extract_fields_sem_inventar(self):
        result = wm._extract_update_fields_via_llm("Pedro", "coloque o Pedro como filho")
        bad = {"tone", "guidelines", "summary", "intent", "frequency"}
        found_bad = bad & set(result.keys())
        self.assertEqual(found_bad, set(), f"LLM inventou campos não permitidos: {found_bad}")

    def test_datetime_context_block(self):
        block = wm._datetime_context_block()
        self.assertIn("DATA E HORA ATUAL", block)
        self.assertIn("/", block)  # data no formato DD/MM/YYYY

    def test_status_expirado(self):
        from datetime import datetime, timedelta
        passado = (datetime.now() - timedelta(hours=2)).isoformat()
        wm._save_owner_status("teste", passado, "raw")
        status = wm._get_active_owner_status()
        self.assertIsNone(status, "Status expirado deveria retornar None")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Filtrar args do unittest
    sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if not a.startswith("--")]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    if RUN_QUICK:
        suite.addTests(loader.loadTestsFromTestCase(TestNormalizacao))
    else:
        suite.addTests(loader.loadTestsFromTestCase(TestNormalizacao))
        suite.addTests(loader.loadTestsFromTestCase(TestBuscaContatos))
        if RUN_LLM:
            suite.addTests(loader.loadTestsFromTestCase(TestLLM))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
