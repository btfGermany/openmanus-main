# VentiAgent - Plattform für KI-Agenten

<div align="center">
  <img src="https://img.shields.io/badge/Version-0.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/Lizenz-MIT-green" alt="Lizenz">
  <img src="https://img.shields.io/badge/Python-3.12+-yellow" alt="Python">
</div>

## Was ist VentiAgent?

VentiAgent ist eine Open-Source-Plattform für den Aufbau universeller KI-Agenten. Die Plattform ermöglicht es, verschiedene Aufgaben mit einer Kombination aus lokalen Werkzeugen und MCP-Servern (Model Context Protocol) zu lösen.

### Hauptmerkmale

- **Universeller Agent**: Kann vielfältige Aufgaben wie Programmierung, Informationsbeschaffung, Dateiverarbeitung und Web-Browsing ausführen
- **Tool-Unterstützung**: Integriert Python-Ausführung, Browser-Automatisierung, Dateibearbeitung und mehr
- **MCP-Server**: Unterstützt Verbindung zu externen MCP-Servern für erweiterte Funktionalität
- **Sandbox-Umgebung**: Arbeitet sicher in isolierten Umgebungen für Code-Ausführung
- **A2A-Protokoll**: Unterstützt das Agent-to-Agent-Kommunikationsprotokoll

## Schnellstart

### Voraussetzungen

- Python 3.12 oder höher
- LLM API-Zugang (OpenAI, Anthropic, Ollama, etc.)

### Installation

```bash
# Repository klonen
git clone https://github.com/FoundationAgents/VentiAgent.git
cd VentiAgent

# Virtuelle Umgebung erstellen
conda create -n ventiagent python=3.12
conda activate ventiagent

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### Konfiguration

1. Kopieren Sie die Beispielkonfiguration:
```bash
cp config/config.example config/config.toml
```

2. Bearbeiten Sie die `config.toml` und fügen Sie Ihren LLM API-Schlüssel hinzu:

```toml
[llm]
provider = "openai"  # oder "anthropic", "ollama", etc.
api_key = "Ihr-API-Schlüssel"
model = "gpt-4o"    # oder anderes Modell
```

### Ausführung

#### Einfacher Einzeiler

```bash
python main.py --prompt "Ihre Anfrage hier"
```

#### Mit Eingabeaufforderung

```bash
python main.py
# Geben Sie Ihre Anfrage ein, wenn Sie dazu aufgefordert werden
```

## Verfügbare Agenten

### VentiAgent (Standard)

Der universelle Haupt-Agent mit Unterstützung für:
- Python-Codeausführung
- Browser-Automatisierung
- Dateibearbeitung
- MCP-Tool-Verbindungen

### DataAnalysis Agent

Für Datenanalyse und Visualisierung geeignet. In `config.toml` zur `run_flow`-Konfiguration hinzufügen.

## Werkzeuge

VentiAgent verfügt über folgende eingebaute Werkzeuge:

| Werkzeug | Beschreibung |
|---------|---------------|
| PythonExecute | Python-Code sicher ausführen |
| Browser | Webbrowsing und HTML-Analyse |
| StrReplaceEditor | Dateien lesen und bearbeiten |
| Terminate | Sitzung beenden |

## MCP-Server Integration

Verbinden Sie externe MCP-Server für erweiterte Funktionalität:

```toml
[mcp_config.servers.mein_server]
type = "sse"
url = "http://localhost:8000"
```

## Entwicklung

### Ordnerstruktur

```
ventiagent/
├── app/                    # Hauptanwendungscode
│   ├── agent/            # Agent-Implementierungen
│   ├── prompt/          # Prompt-Vorlagen
│   ├── tool/           # Werkzeug-Implementierungen
│   ├── sandbox/        # Sandbox-Umgebung
│   └── mcp/           # MCP-Server
├── config/               # Konfigurationsdateien
├── tests/               # Tests
└── protocol/            # Protokoll-Implementierungen
```

### Tests ausführen

```bash
pytest tests/
```

## Lizenz

PROPRIETÄRE LIZENZ - NUR MIT GENEHMIGUNG NUTZBAR

DIESE SOFTWARE IST NICHT FREI VERFÜGBAR. Die Nutzung, Vervielfältigung, 
Verbreitung, Modifikation, Sublizenzierung oder jegliche andere 
Verwendung dieser Software ohne ausdrückliche schriftliche Genehmigung der 
Repository-Eigentümer ist ausdrücklich verboten.

Eine Genehmigung kann schriftlich bei den Eigentümern des Repositories 
eingeholt werden. Kontaktieren Sie bitte die Repository-Eigentümer, bevor Sie 
diese Software nutzen, kopieren, modifizieren oder verbreiten.

## Danksagungen

VentiAgent wurde von Mitwirkenden der MetaGPT-Community entwickelt. Vielen Dank an diese aktive Agenten-Entwicklercommunity!

## Zitat

```bibtex
@misc{ventiagent2025,
  title = {VentiAgent: An open-source framework for building general AI agents},
  author = {VentiAgent Team},
  year = {2025},
  howpublished = {\url{https://github.com/FoundationAgents/VentiAgent}}
}
```