"""
Suíte de Testes Unitários para a Expansão Cortical v3.0:
- `ExtendedCognitiveCortexV3`: 10 Neurônios Especialistas em 4 Lobos Corticais (+ Tálamo + Convergência = 12 Nós).
- `SynapticPlasticityMemory`: Hipocampo de aprendizado contínuo de restrições negativas e invariantes destilados.
- Projeção do Hipocampo e dos 12 Neurônios no Vault do Obsidian (`06_Sabedoria_Consolidada_Hipocampo/`).
"""

from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(_ROOT.parent))

from core.event_store import EpistemicEventStore
from core.extended_cortex_v3 import (
    EXTENDED_SPECIALISTS_SPEC,
    ExtendedCognitiveCortexV3,
    SynapticPlasticityMemory,
)
from core.obsidian_bridge import NEURON_HUB_MAP, ObsidianVaultBridge
from core.schemas import VerdictStatus


class TestExtendedCognitiveBrainV3(unittest.TestCase):
    def test_01_twelve_neural_nodes_registered_and_mapped(self) -> None:
        """Garante que o Córtex v3.0 registre os 10 especialistas (+ Tálamo + Convergência = 12 nós base no mapa)."""
        self.assertEqual(len(EXTENDED_SPECIALISTS_SPEC), 10)
        self.assertGreaterEqual(len(NEURON_HUB_MAP), 12)

        cortex = ExtendedCognitiveCortexV3()
        for spec in EXTENDED_SPECIALISTS_SPEC:
            self.assertIn(spec["neuron_id"], cortex.specialist_neurons)

    def test_02_topological_waves_of_extended_10_specialist_dag(self) -> None:
        """Verifica que o DAG v3.0 compila 10 nós especialistas divididos em ondas topológicas sem ciclos."""
        cortex = ExtendedCognitiveCortexV3()
        dag = cortex.compile_extended_dag("Auditar criptografia pós-quântica e inferência causal")
        self.assertEqual(len(dag.nodes), 10)

        waves = dag.topological_generations()
        self.assertEqual(len(waves), 4)
        self.assertEqual(len(waves[0]), 3)  # Onda 1: Lógica, Fatos, Criptografia
        self.assertEqual(len(waves[1]), 3)  # Onda 2: Engenharia, Risco, Causal/Contrafactual
        self.assertEqual(len(waves[2]), 3)  # Onda 3a: Metacognição, Hipocampo, Planejador Recursivo
        self.assertEqual(len(waves[3]), 1)  # Onda 3b: Semântica e Didática (consolida 3a)

    def test_03_execute_extended_v3_and_harvest_synaptic_plasticity(self) -> None:
        """Executa os 10 especialistas em DAG e verifica a colheita automática de sabedoria no Hipocampo."""
        store = EpistemicEventStore(":memory:")
        plasticity = SynapticPlasticityMemory(":memory:")
        try:
            # Registra uma restrição negativa prévia para validar injeção sináptica
            plasticity.record_rule(
                neuron_id="neuron_crypto_security",
                rule_type="NEGATIVE_CONSTRAINT",
                rule_text="Proibido reutilizar nonce em esquemas de cifra de fluxo ou EdDSA.",
                source_event_id="evt_genesis_rule",
            )

            cortex = ExtendedCognitiveCortexV3(event_store=store, plasticity_memory=plasticity)
            res = cortex.process_v3("Projetar arquitetura distribuída Zero-Trust com auditoria metacognitiva")

            self.assertEqual(res.status, VerdictStatus.APPROVED)
            self.assertEqual(res.total_nodes, 10)
            self.assertEqual(res.executed_nodes, 10)
            self.assertEqual(len(res.certificates), 10)
            self.assertTrue(res.integrity_verified)

            rules = plasticity.list_all_rules()
            self.assertGreaterEqual(len(rules), 10)
        finally:
            plasticity.close()
            store.close()

    def test_04_project_12_neurons_and_hippocampus_to_obsidian_vault(self) -> None:
        """Verifica que os 12 hubs neurais e a pasta 06_Sabedoria_Consolidada_Hipocampo são criados no Vault."""
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "MY BRAIN"
            bridge = ObsidianVaultBridge(vault_dir)
            bridge.initialize_vault_structure()

            neuron_files = list((bridge.vault_root / bridge.DIR_NEURONS).glob("*.md"))
            self.assertEqual(len(neuron_files), 12)

            plasticity = SynapticPlasticityMemory(":memory:")
            try:
                plasticity.record_rule(
                    neuron_id="neuron_logic_math",
                    rule_type="NEGATIVE_CONSTRAINT",
                    rule_text="Evitar divisão sem verificação de denominador não-nulo.",
                    source_event_id="evt_rb_01",
                )
                hippo_note = bridge.project_plasticity_to_vault(plasticity)
                self.assertTrue(hippo_note.exists())
                text = hippo_note.read_text(encoding="utf-8")
                self.assertIn("Anticorpos Epistêmicos", text)
                self.assertIn("Evitar divisão sem verificação", text)
            finally:
                plasticity.close()

    def test_05_dynamic_neurogenesis_spawns_and_reuses_distant_domain_neuron(self) -> None:
        """
        Valida que um assunto distante dos 10 especialistas atuais dispara a Neurogênese Dinâmica,
        cria um 11º especialista persistente + nota no Obsidian, e o reutiliza em chamadas futuras!
        """
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "MY BRAIN"
            bridge = ObsidianVaultBridge(vault_dir)
            bridge.initialize_vault_structure()

            store = EpistemicEventStore(":memory:")
            plasticity = SynapticPlasticityMemory(":memory:")
            try:
                cortex = ExtendedCognitiveCortexV3(event_store=store, plasticity_memory=plasticity)

                # 1ª chamada sobre micro-conceito (Bioquímica & Dobramento de Proteínas)
                # Deve abstrair para a Grande Área: Biologia & Medicina (neuron_dyn_biologia_e_medicina)
                distant_prompt = "Modelar bioquimica farmacologica de dobramento molecular de proteinas"
                res1 = cortex.process_v3(distant_prompt)
                self.assertEqual(res1.status, VerdictStatus.APPROVED)
                self.assertEqual(res1.total_nodes, 11)  # 10 nativos + 1 Macro-Neurônio nascido por Neurogênese!

                spawned_list = plasticity.list_spawned_neurons()
                self.assertEqual(len(spawned_list), 1)
                dyn_spec = spawned_list[0]
                self.assertEqual(dyn_spec.neuron_id, "neuron_dyn_biologia_e_medicina")
                self.assertEqual(dyn_spec.note_name, "Neuronio_Dinamico_Biologia_e_Medicina")
                self.assertEqual(dyn_spec.activations_count, 1)

                # Projetar no Obsidian e verificar se a nota do Macro-Neurônio nasceu em 03_Neuronios_Especialistas
                bridge.project_cortex_run_to_vault(res1, objective=distant_prompt, event_store=store)
                dyn_note = bridge.vault_root / bridge.DIR_NEURONS / f"{dyn_spec.note_name}.md"
                self.assertTrue(dyn_note.exists(), f"Nota do neurônio dinâmico deveria existir: {dyn_note}")

                # 2ª chamada sobre OUTRO sub-assunto da mesma Grande Área (Genética CRISPR e Metabolismo)
                # Deve REUTILIZAR o mesmo Macro-Neurônio neuron_dyn_biologia_e_medicina sem criar outro!
                sp2, newly_spawned = plasticity.detect_or_spawn_domain_neuron(
                    "Edicao genetica CRISPR e fisiologia do metabolismo celular"
                )
                self.assertIsNotNone(sp2)
                self.assertFalse(newly_spawned)
                self.assertEqual(sp2.neuron_id, "neuron_dyn_biologia_e_medicina")
                self.assertEqual(sp2.activations_count, 2)
                self.assertEqual(len(plasticity.list_spawned_neurons()), 1)

                # 3ª chamada sobre Dilatação Temporal -> Deve abstrair para Física Avançada (neuron_dyn_fisica_avancada)
                sp3, newly_spawned_phys = plasticity.detect_or_spawn_domain_neuron("DILATAÇÃO TEMPORAL APLICADA")
                self.assertIsNotNone(sp3)
                self.assertTrue(newly_spawned_phys)
                self.assertEqual(sp3.neuron_id, "neuron_dyn_fisica_avancada")
                self.assertEqual(sp3.note_name, "Neuronio_Dinamico_Fisica_Avancada")
            finally:
                plasticity.close()
                store.close()


if __name__ == "__main__":
    unittest.main()
