<p align="center">
  <img src="assets/logo.jpg" width="200"/>
</p>

[English](README.md) | [中文](README_zh.md) | [한국어](README_ko.md) | [日本語](README_ja.md) | [Deutsch](README_DE.md)

[![GitHub stars](https://img.shields.io/github/stars/FoundationAgents/OpenManus?style=social)](https://github.com/FoundationAgents/OpenManus/stargazers)
&ensp;
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Discord Follow](https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat)](https://discord.gg/DYn29wFk9z)
[![Demo](https://img.shields.io/badge/Demo-Hugging%20Face-yellow)](https://huggingface.co/spaces/lyh-917/OpenManusDemo)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15186407.svg)](https://doi.org/10.5281/zenodo.15186407)

# Willkommen

Dieses Projekt bietet eine Plattform für KI-Agenten, die verschiedene Aufgaben ausführen können.

## Projekt-Features

- **Universeller Agent**: Kann vielfältige Aufgaben wie Programmierung, Informationsbeschaffung, Dateiverarbeitung und Web-Browsing ausführen
- **Tool-Unterstützung**: Integriert Python-Ausführung, Browser-Automatisierung, Dateibearbeitung und mehr
- **MCP-Server**: Unterstützt Verbindung zu externen MCP-Servern für erweiterte Funktionalität
- **Sandbox-Umgebung**: Arbeitet sicher in isolierten Umgebungen für Code-Ausführung
- **A2A-Protokoll**: Unterstützt das Agent-to-Agent-Kommunikationsprotokoll

## Installation

Wir bieten zwei Installationsmethoden. Methode 2 (mit uv) wird für schnellere Installation empfohlen.

### Methode 1: Mit conda

1. Erstellen Sie eine neue conda-Umgebung:

```bash
conda create -n agent_platform python=3.12
conda activate agent_platform
```

2. Klonen Sie das Repository:

```bash
git clone https://github.com/FoundationAgents/OpenManus.git
cd OpenManus
```

3. Installieren Sie Abhängigkeiten:

```bash
pip install -r requirements.txt
```

### Methode 2: Mit uv (Empfohlen)

1. Installieren Sie uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Klonen Sie das Repository:

```bash
git clone https://github.com/FoundationAgents/OpenManus.git
cd OpenManus
```

3. Erstellen und aktivieren Sie eine virtuelle Umgebung:

```bash
uv venv --python 3.12
source .venv/bin/activate  # Unter Unix/macOS
# Oder unter Windows:
# .venv\Scripts\activate
```

4. Installieren Sie Abhängigkeiten:

```bash
uv pip install -r requirements.txt
```

### Browser-Automatisierung (Optional)
```bash
playwright install
```

## Konfiguration

Dieses Projekt erfordert Konfiguration für die verwendeten LLM-APIs. Folgen Sie diesen Schritten:

1. Erstellen Sie eine `config.toml`-Datei im `config`-Verzeichnis:

```bash
cp config/config.example.toml config/config.toml
```

2. Bearbeiten Sie `config/config.toml` für Ihre API-Schlüssel:

```toml
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Ersetzen Sie mit Ihrem API-Schlüssel
max_tokens = 4096
temperature = 0.0
```

## Schnellstart

Einzeiler zum Starten:

```bash
python main.py
```

Geben Sie dann Ihre Anfrage ein!

Für MCP-Tools:
```bash
python run_mcp.py
```

Für Multi-Agent-Version:

```bash
python run_flow.py
```

### Mehrere Agenten hinzufügen

Neben dem allgemeinen Agenten ist auch ein DataAnalysis-Agent integriert. Fügen Sie ihn in `config.toml` hinzu:

```toml
[runflow]
use_data_analysis_agent = true
```

## Mitwirkende

Wir danken allen Mitwirkenden dieses Projekts!

## Danksagungen

Wir danken folgenden Projekten für ihre Unterstützung:
- anthropic-computer-use
- browser-use
- crawl4ai
- MetaGPT
- OpenHands
- SWE-agent

## Lizenz

PROPRIETÄRE LIZENZ - NUR MIT GENEHMIGUNG NUTZBAR

Nähere Informationen entnehmen Sie der LICENSE-Datei.

## Zitat
```bibtex
@misc{agent2025,
  title = {KI-Agenten-Plattform},
  year = {2025},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.15186407},
  url = {https://doi.org/10.5281/zenodo.15186407},
}
```
