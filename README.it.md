# 🔥 Fiamma

🇬🇧 [English](README.md) · 🇮🇹 **Italiano**

**Fiamma ti aiuta a concentrarti.** Lavori 25 minuti senza distrazioni, poi fai 5 minuti di pausa. Ogni 4 giri ti spetta una pausa più lunga. Questo metodo si chiama *tecnica del pomodoro*: ogni blocco da 25 minuti è un "pomodoro" 🍅.

## Cosa fa, in parole semplici

1. **Premi il pulsante grande e inizi a lavorare.** Un anello colorato si riempie man mano che passa il tempo.
2. **Quando il tempo finisce, Fiamma suona e ti dice di fare una pausa.** Dopo la pausa ti avvisa di nuovo per ricominciare.
3. **Scrivi le cose che devi fare** nella scheda *Attività* e scegli quella su cui stai lavorando. Fiamma conta quanti pomodori ci hai dedicato.
4. **Guardi i tuoi progressi** nella scheda *Statistiche*: quanto hai lavorato oggi, quanti giorni di fila, il grafico della settimana e un obiettivo giornaliero da raggiungere.

Funziona tutto sul tuo computer, senza internet e senza account. I dati restano in `~/.local/share/fiamma/data.json`.

## Funzionalità

- **Timer** con anello animato che cambia colore: corallo per la concentrazione, azzurro per la pausa breve, viola per la pausa lunga
- **Pausa lunga automatica** ogni N pomodori (di default 4), con puntini che mostrano a che punto sei del ciclo
- **Attività**: ogni pomodoro completato viene contato sull'attività scelta; puoi annullare un'eliminazione
- **Statistiche**: pomodori e minuti di oggi, giorni consecutivi 🔥, ore totali, obiettivo giornaliero, grafico degli ultimi 7 giorni, attività più lavorate
- Suono di fine sessione, notifiche di sistema, tema chiaro/scuro automatico, layout che si adatta anche alle finestre strette
- Durate, obiettivo e avvio automatico delle sessioni configurabili dalle preferenze

## Installazione

Serve Linux con GNOME (o comunque GTK4 e libadwaita ≥ 1.5). Su Debian/Ubuntu/Fedora con GNOME è già tutto presente; altrimenti installa `python3-gi`, `python3-gi-cairo` e `gir1.2-adw-1`.

```bash
git clone <url-del-repository>
cd fiamma
./fiamma.py      # per provarla subito
./install.sh     # per aggiungerla al menu delle applicazioni (comando: fiamma)
```

L'installazione avviene solo nella tua cartella utente, senza permessi di amministratore.

## Scorciatoie da tastiera

| Tasto | Azione |
|---|---|
| Spazio | Avvia / metti in pausa |
| R | Azzera il timer |
| N | Passa alla sessione successiva |
| Ctrl + , | Preferenze |
| Ctrl + Q | Esci |

## Licenza

MIT
