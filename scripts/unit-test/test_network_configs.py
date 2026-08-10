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

    def test_extreme_dns_server(self):
        # Estrae il dns_server del L3 Core Switch (extreme)
        switch_node = next((n for n in self.rete_data.get('nodi', []) if n.get('id') == 'extreme'), None)
        self.assertIsNotNone(switch_node, "Nodo extreme non trovato in rete.json")
        self.assertEqual(switch_node.get('dns_server'), '192.168.2.254', "extreme dns_server non è 192.168.2.254")

    def test_vlan20_interface_has_ip(self):
        """gw-vlan20 deve avere un IP valido nella subnet 10.10.20.0/24."""
        opnsense_node = next((n for n in self.rete_data.get('nodi', []) if n.get('id') == 'opnsense'), None)
        self.assertIsNotNone(opnsense_node)
        found = False
        for port in opnsense_node.get('ports', []):
            for li in port.get('logical_interfaces', []):
                if li.get('name') == 'gw-vlan20':
                    found = True
                    ip = li.get('ip', '')
                    self.assertTrue(
                        ip.startswith('10.10.20.'),
                        f"gw-vlan20 deve avere IP in 10.10.20.0/24, trovato: {ip}"
                    )
        self.assertTrue(found, "Interfaccia gw-vlan20 non trovata")

    def test_vlan10_interface_is_none(self):
        """gw-vlan10 deve rimanere senza IP (static_only, non modificata)."""
        opnsense_node = next((n for n in self.rete_data.get('nodi', []) if n.get('id') == 'opnsense'), None)
        self.assertIsNotNone(opnsense_node)
        found = False
        for port in opnsense_node.get('ports', []):
            for li in port.get('logical_interfaces', []):
                if li.get('name') == 'gw-vlan10':
                    found = True
                    self.assertEqual(li.get('ip'), 'None',
                        "gw-vlan10 deve rimanere None (VLAN 10 = static only)")
        self.assertTrue(found, "Interfaccia gw-vlan10 non trovata")

    def test_vlan20_dhcp_fields_complete(self):
        """VLAN 20 dhcp block deve avere tutti i campi richiesti dalla pipeline."""
        vlan20 = next((v for v in self.rete_data.get('VLAN', []) if v.get('id') == '20'), None)
        self.assertIsNotNone(vlan20, "VLAN 20 non trovata")
        dhcp = vlan20.get('dhcp', {})
        required = ['gateway', 'dns', 'domain', 'mode', 'opnsense_ip', 'pool_start', 'pool_end']
        for field in required:
            self.assertIn(field, dhcp, f"Campo DHCP mancante in VLAN 20: {field}")
        self.assertEqual(dhcp['gateway'], '10.10.20.1',
            "Il gateway DHCP di VLAN 20 deve essere il L3 Switch, non OPNsense")
        self.assertEqual(dhcp['mode'], 'direct')

if __name__ == '__main__':
    unittest.main()
