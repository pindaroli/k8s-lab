import unittest
import json
import os

class TestNetworkConfigs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Trova la root del progetto e carica rete.json
        cls.script_dir = os.path.dirname(os.path.abspath(__file__))
        cls.project_root = os.path.abspath(os.path.join(cls.script_dir, '../../'))
        cls.rete_path = os.path.join(cls.project_root, 'rete.json')

        with open(cls.rete_path, 'r') as f:
            cls.rete_data = json.load(f)

    def test_opnsense_oob_ip(self):
        # Estrae il management_ip di OPNsense (OOB)
        opnsense_node = next((n for n in self.rete_data.get('nodi', []) if n.get('id') == 'opnsense'), None)
        self.assertIsNotNone(opnsense_node, "Nodo OPNsense non trovato in rete.json")
        self.assertEqual(opnsense_node.get('management_ip'), '192.168.100.1', "OPNsense management_ip non è 192.168.100.1")

    def test_switch10g_dns_server(self):
        # Estrae il dns_server di switch10g (Transit DNS)
        switch_node = next((n for n in self.rete_data.get('nodi', []) if n.get('id') == 'switch10g'), None)
        self.assertIsNotNone(switch_node, "Nodo switch10g non trovato in rete.json")
        self.assertEqual(switch_node.get('dns_server'), '192.168.2.254', "switch10g dns_server non è 192.168.2.254")

    def test_logical_interfaces_clean(self):
        # Verifica che le interfacce gw-vlan10 e gw-vlan20 abbiano IP impostato a "None"
        opnsense_node = next((n for n in self.rete_data.get('nodi', []) if n.get('id') == 'opnsense'), None)
        self.assertIsNotNone(opnsense_node)

        for port in opnsense_node.get('ports', []):
            for log_iface in port.get('logical_interfaces', []):
                if log_iface.get('name') in ['gw-vlan10', 'gw-vlan20']:
                    self.assertEqual(log_iface.get('ip'), 'None', f"L'IP dell'interfaccia {log_iface.get('name')} non è 'None'")

if __name__ == '__main__':
    unittest.main()
