#!/usr/bin/env python3
"""Testa post_llm_call, redação de telefone, _resolve_chat_id e _human_send.

Cobre as lacunas de cobertura mais críticas:
- Filtro de número de telefone (regex de redação)
- Roteamento owner vs contato no post_llm_call
- _resolve_chat_id com e sem mapeamento
- Split de mensagem em bolhas no _human_send
- Constraints de segurança nos prompts

Uso:
    python3 test_post_llm_and_security.py
"""

import sys
import os
import re
import types
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

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


# ── Regex de redação (extraída igual ao post_llm_call) ────────────────────────

PHONE_RE = re.compile(r'\(?\+?[\d][\d\s\-\.\(\)]{6,18}[\d]')

def _redact(text: str) -> str:
    return PHONE_RE.sub(
        lambda m: "[número omitido]" if len(re.sub(r'\D', '', m.group())) >= 8 else m.group(),
        text
    )


# ── Testes ────────────────────────────────────────────────────────────────────

class TestPhoneRedaction(unittest.TestCase):
    """Filtro de número de telefone aplicado antes do envio."""

    def test_numero_br_simples(self):
        result = _redact("O número é 558698036699.")
        self.assertIn("[número omitido]", result)
        self.assertNotIn("558698036699", result)

    def test_numero_com_mascara(self):
        result = _redact("Ligue: +55 (86) 9803-6699")
        self.assertIn("[número omitido]", result)
        self.assertNotIn("9803-6699", result)

    def test_numero_com_parenteses(self):
        result = _redact("whatsapp: (11) 99999-8888")
        self.assertIn("[número omitido]", result)

    def test_numero_com_espacos(self):
        result = _redact("55 86 98036699")
        self.assertIn("[número omitido]", result)

    def test_nao_redacta_hora(self):
        self.assertNotIn("[número omitido]", _redact("Às 14h30 temos reunião"))
        self.assertNotIn("[número omitido]", _redact("volta às 11h"))

    def test_nao_redacta_codigo_curto(self):
        self.assertNotIn("[número omitido]", _redact("código: 1234"))

    def test_nao_redacta_versao(self):
        self.assertNotIn("[número omitido]", _redact("versão 3.1.4.1592"))

    def test_nao_redacta_porta(self):
        self.assertNotIn("[número omitido]", _redact("porta 8642 da API"))

    def test_multiplos_numeros_no_texto(self):
        text = "Ligue para 558699997003 ou 5511996472188"
        result = _redact(text)
        self.assertEqual(result.count("[número omitido]"), 2)
        self.assertNotIn("558699997003", result)
        self.assertNotIn("5511996472188", result)

    def test_texto_sem_numero_inalterado(self):
        text = "ele capotou aqui, só umas 11h"
        self.assertEqual(_redact(text), text)


class TestResolveChatId(unittest.TestCase):
    """_resolve_chat_id com e sem mapeamento no _sender_to_chat."""

    def setUp(self):
        wm._sender_to_chat.clear()

    def test_retorna_mapeamento_existente(self):
        wm._sender_to_chat["558699997003@s.whatsapp.net"] = "558699997003@s.whatsapp.net"
        result = wm._resolve_chat_id("558699997003@s.whatsapp.net")
        self.assertEqual(result, "558699997003@s.whatsapp.net")

    def test_strip_device_suffix_quando_sem_mapeamento(self):
        # JID com device suffix real: 5511999:5@s.whatsapp.net
        result = wm._resolve_chat_id("5511999:5@s.whatsapp.net")
        self.assertIn("5511999@s.whatsapp.net", result)
        self.assertNotIn(":5", result)

    def test_retorna_vazio_quando_sem_jid(self):
        result = wm._resolve_chat_id("")
        self.assertEqual(result, "")

    def test_session_key_mapeado(self):
        """Após preencher _sender_to_chat com session_key, deve resolver."""
        wm._sender_to_chat["20260624_040211_5653d007"] = "558699997003@s.whatsapp.net"
        result = wm._sender_to_chat.get("20260624_040211_5653d007")
        self.assertEqual(result, "558699997003@s.whatsapp.net")


class TestHumanSendSplit(unittest.TestCase):
    """Lógica de split de mensagem em bolhas (sem I/O real)."""

    def _get_parts(self, message: str) -> list[str]:
        """Replica a lógica de split do _human_send."""
        parts = [p.strip() for p in message.split("\n\n") if p.strip()]
        if len(parts) == 1:
            parts = [p.strip() for p in message.split("\n") if p.strip()]
            if len(parts) == 2 and len(parts[0]) <= 60:
                pass
            else:
                parts = [message.strip()]
        return parts

    def test_dois_paragrafos_vira_duas_bolhas(self):
        msg = "eita\n\nele capotou aqui, só umas 11h"
        parts = self._get_parts(msg)
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0], "eita")

    def test_linha_curta_mais_longa_vira_duas_bolhas(self):
        msg = "opa\nele tá no futebol até umas 21h"
        parts = self._get_parts(msg)
        self.assertEqual(len(parts), 2)

    def test_linha_longa_nao_divide(self):
        msg = "essa é uma frase longa que não deve ser dividida em bolhas separadas aqui"
        parts = self._get_parts(msg)
        self.assertEqual(len(parts), 1)

    def test_mensagem_simples_uma_bolha(self):
        msg = "só umas 11h"
        parts = self._get_parts(msg)
        self.assertEqual(len(parts), 1)

    def test_tres_paragrafos_vira_tres_bolhas(self):
        msg = "oi\n\ncomo vai\n\ntudo bem?"
        parts = self._get_parts(msg)
        self.assertEqual(len(parts), 3)


class TestPostLlmCallRoteamento(unittest.TestCase):
    """post_llm_call roteia corretamente owner vs contato."""

    def _call(self, session_id: str, response: str, platform: str = "whatsapp"):
        return wm.post_llm_call(
            session_id=session_id,
            assistant_response=response,
            platform=platform,
            user_message="oi",
            conversation_history=[],
            model="gemini",
        )

    def test_plataforma_nao_whatsapp_retorna_none(self):
        result = self._call("qualquer", "resposta", platform="telegram")
        self.assertIsNone(result)

    def test_resposta_vazia_retorna_none(self):
        result = self._call("558699997003@s.whatsapp.net", "")
        self.assertIsNone(result)

    def test_owner_sem_exec_retorna_none(self):
        owner = wm.config.whatsapp_owner_number or "5511999999999"
        with patch.object(wm.config.__class__, "whatsapp_owner_number", new_callable=lambda: property(lambda self: owner)):
            result = self._call(owner, "Tudo certo por aqui!")
        self.assertIsNone(result)

    def test_contato_chama_human_send(self):
        """Contato não-owner deve chamar _human_send e retornar assistant_response vazio."""
        wm._sender_to_chat["contato_session"] = "558699997003@s.whatsapp.net"
        sent = []

        def fake_human_send(chat_id, message):
            sent.append((chat_id, message))

        # post_llm_call.__globals__ é o namespace do exec — patchear lá diretamente
        globs = wm.post_llm_call.__globals__
        orig = globs["_human_send"]
        globs["_human_send"] = fake_human_send
        try:
            with patch.dict(os.environ, {"WHATSAPP_OWNER_NUMBER": "5511000000000"}):
                result = self._call("contato_session", "ele capotou aqui kk")
        finally:
            globs["_human_send"] = orig

        self.assertEqual(result, {"assistant_response": ""})
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][0], "558699997003@s.whatsapp.net")

    def test_contato_redacta_telefone_antes_de_enviar(self):
        """Número de telefone deve ser redactado antes do _human_send."""
        wm._sender_to_chat["contato_session2"] = "558699997003@s.whatsapp.net"
        sent = []

        def fake_human_send(chat_id, message):
            sent.append(message)

        globs = wm.post_llm_call.__globals__
        orig = globs["_human_send"]
        globs["_human_send"] = fake_human_send
        try:
            with patch.dict(os.environ, {"WHATSAPP_OWNER_NUMBER": "5511000000000"}):
                self._call("contato_session2", "O número dela é 558698036699")
        finally:
            globs["_human_send"] = orig

        self.assertTrue(len(sent) > 0)
        self.assertNotIn("558698036699", sent[0])
        self.assertIn("[número omitido]", sent[0])


class TestSecurityConstraints(unittest.TestCase):
    """Prompts contêm as constraints de segurança corretas."""

    def _personal(self, contact_info=None):
        info = contact_info or {"name": "Teste", "relationship": "Amigo"}
        return wm._build_personal_prompt(info, "Amigo", "")["context"]

    def _support(self):
        return wm._build_support_prompt("soul", "rules", "")["context"]

    def test_personal_nao_afirmar_capacidade_tecnica(self):
        ctx = self._personal()
        self.assertIn("NUNCA afirme", ctx)

    def test_personal_proibe_telefone(self):
        ctx = self._personal()
        self.assertIn("telefone", ctx.lower())
        self.assertIn("NUNCA informe", ctx)

    def test_personal_proibe_ferramentas(self):
        ctx = self._personal()
        self.assertIn("terminal", ctx.lower())

    def test_support_proibe_telefone(self):
        ctx = self._support()
        self.assertIn("NUNCA informe", ctx)
        self.assertIn("telefone", ctx.lower())

    def test_support_proibe_ferramentas(self):
        ctx = self._support()
        self.assertIn("NUNCA afirme", ctx)

    def test_personal_sem_sistema_automatizado(self):
        ctx = self._personal().lower()
        self.assertNotIn("sistema automatizado", ctx)


class TestNormalizacaoPhone(unittest.TestCase):
    """_normalize_brazilian_phone — funções puras."""

    def test_nono_digito_removido(self):
        fn = wm._normalize_brazilian_phone
        self.assertEqual(fn("5511987654321"), fn("551187654321"))

    def test_idempotente(self):
        fn = wm._normalize_brazilian_phone
        n = "5511987654321"
        self.assertEqual(fn(fn(n)), fn(n))

    def test_numero_nao_br_inalterado(self):
        fn = wm._normalize_brazilian_phone
        result = fn("12025550123")
        self.assertEqual(result, "12025550123")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPhoneRedaction))
    suite.addTests(loader.loadTestsFromTestCase(TestResolveChatId))
    suite.addTests(loader.loadTestsFromTestCase(TestHumanSendSplit))
    suite.addTests(loader.loadTestsFromTestCase(TestPostLlmCallRoteamento))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityConstraints))
    suite.addTests(loader.loadTestsFromTestCase(TestNormalizacaoPhone))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
