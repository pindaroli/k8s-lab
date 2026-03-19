# Guida alla Migrazione: Symmetric Routing (L3 Switch + OPNsense)

Questa guida ti accompagna passo passo nella transizione dalla tua attuale configurazione di **Asymmetric Routing** a una di **Symmetric Routing** puro.

## Cosa Cambia?
*   **Prima (Asymmetric)**: OPNsense ha un indirizzo IP in ciascuna VLAN (es. `10.10.10.254`, `10.10.20.254`). Il traffico passava dallo switch, usciva verso Internet via OPNsense, ma OPNsense rispondeva bypassando lo switch sulla VLAN nativa.
*   **Dopo (Symmetric)**: OPNsense comunicherà con la tua rete **esclusivamente** tramite la rete `TRANSIT` (`192.168.2.254`). Lo switch ONTi L3 diventa l'unico padrone del traffico interno. OPNsense farà solo da porta blindata verso Internet.

> [!CAUTION]
> **Rischio Disconnessione**: Esegui queste modifiche partendo dalla **Porta ADMIN/Management** dedicata di OPNsense (es. `igc3` / `192.168.100.1`) o tenendo un portatile configurato con IP fisso sulla rete di Transito.

---

## FASE 1: Preparazione OPNsense (Routing e DNS)

1.  **Imposta le Rotte Statiche in OPNsense**
    OPNsense non essendo più connesso direttamente alle VLAN 10, 20 e 30, deve sapere che per raggiungerle deve passare dallo Switch.
    *   Vai in **System** > **Routes** > **Configuration**.
    *   Assicurati di avere un **Gateway** configurato che punta all'IP dello switch sulla rete di transito (`192.168.2.1`).
    *   Assicurati di avere tre rotte statiche:
        *   `10.10.10.0/24` -> Gateway: Switch (`192.168.2.1`)
        *   `10.10.20.0/24` -> Gateway: Switch (`192.168.2.1`)
        *   `10.10.30.0/24` -> Gateway: Switch (`192.168.2.1`)

2.  **Aggiorna il DHCP Server (Sostituzione IP DNS)**
    Visto che gli IP di OPNsense nelle VLAN `10.10.x.254` spariranno, i client non potranno più usare quegli IP come Gateway/DNS. Devono usare l'IP TRANSIT o del Gateway di VLAN.
    *   Vai in **Services** > **DHCPv4** (Dovrai modificare le scope relative alle reti 10, 20, 30, se gestite qui tramite relay).
    *   Modifica il campo **DNS Servers** e **Gateway**.
    *   **Gateway**: deve essere l'IP dello Switch in quella specifica VLAN (es. per VLAN 20: `10.10.20.1`).
    *   **DNS Servers**: imposta a `192.168.2.254` (IP OPNsense su Transit) oppure a un resolver interno (es. un AdGuard se ce l'hai).

3.  **Aggiorna le Listen Interfaces di Unbound DNS**
    *   Vai in **Services** > **Unbound DNS** > **General**.
    *   Sotto **Network Interfaces**, assicurati che `TRANSIT` (o All) sia selezionata.
    *   Verifica che in **Access Lists** le subnet `10.10.10.0/24` e `10.10.20.0/24` abbiano l'azione `Allow` impostata, poiché per Unbound ora sembreranno richieste provenienti da una subnet non direttamente connessa.

4.  **Sposta le Regole Firewall sulla VLAN TRANSIT**
    Tutto il traffico verso/da Internet passerà dalla porta `TRANSIT`. Le regole presenti sulle tab di OPNsense relative a VLAN 10/20 non verranno più colpite in entrata.
    *   Vai in **Firewall** > **Rules** > **TRANSIT**.
    *   Crea una regola `Allow` da `Source: 10.10.0.0/16` verso `Destination: Any` (oppure regole più stringenti se vuoi differenziare l'accesso fra server/client/iot).

---

## FASE 2: Modifiche sullo Switch L3

Adesso diciamo allo Switch di prendersi carico di tutto il routing interno.

1.  **Verifica il Default Gateway dello Switch**
    *   Accedi all'interfaccia dello Switch ONTi.
    *   Controlla che la *Static Route* `0.0.0.0 0.0.0.0` punti a **`192.168.2.254`** (OPNsense TRANSIT).

2.  **Verifica il DHCP Relay**
    Poiché OPNsense non ha più porte a livello 2 nelle VLAN, le richieste DHCP broadcastate dai client devono essere impacchettate e spedite dallo Switch (DHCP Helper).
    *   Vai su configurazione **DHCP Relay**.
    *   Per la VLAN 10, 20 e 30, il `Helper-server Address` o `DHCP Relay IP` deve puntare a **`192.168.2.254`**.

---

## FASE 3: Il Taglio Finale (OPNsense Cleanup)

Questa è la fase in cui abbandoniamo definitivamente l'Asymmetric Routing.

1.  **Disconnetti le vecchie interfacce VLAN da OPNsense**
    *   Vai in **Interfaces** > **Assignments**.
    *   Se avevi creato interfacce virtuali (VLAN taggate su igc1) per le VLAN 10, 20 e 30, **eliminale** da qui.
    *   *Nota: OPNsense legacy DHCP fa fatica a servire scope di reti su cui non ha una interfaccia assegnata. Per aggirare il problema, puoi convertire il DHCP server a Kea DHCP o lasciare un IP fittizio assegnato fuori range a un'interfaccia che non scambia traffico.*

2.  **Disattiva lo 'Static Route Filtering'**
    L'hack che permetteva l'Asymmetric Routing senza droppare pacchetti va disabilitato per ridare a OPNsense la sua natura di firewall stateful e simmetrico.
    *   Vai in **Firewall** > **Settings** > **Advanced**.
    *   Cerca **Static route filtering** (o *Bypass firewall rules for traffic on the same interface*).
    *   **Disabilitalo** (togli la spunta).
    *   Clicca **Save**.

3.  **Verifica Outbound NAT**
    *   Vai in **Firewall** > **NAT** > **Outbound**.
    *   Assicurati di avere una regola che trasli (masquerade) le reti interne `10.10.0.0/16` (o le singole vlan) sull'interfaccia WAN.

---

## FASE 4: Validazione e Test

1.  **Test LAN**
    *   Disconnettiti e riconnettiti alla rete dal PC.
    *   Verifica che ricevi correttamente l'indirizzo IP via DHCP dallo Switch/OPNsense.
    *   Controlla che il tuo Gateway sia ora `10.10.20.1` (Switch) e il DNS `192.168.2.254`.
2.  **Test Internet**
    *   Esegui `ping 8.8.8.8` per confermare l'uscita dalla WAN.
3.  **Traceroute**
    *   Esegui `traceroute 8.8.8.8` (o `tracert` su Windows).
    *   Il primo hop DEVE essere l'IP dello Switch (`10.10.x.1`).
    *   Il secondo hop DEVE essere l'IP di Transito di OPNsense (`192.168.2.254`).
    *   *Se questo accade, complimenti, hai attivato con successo il Symmetric Routing!*
