# 🎬 CineTorrent

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![PySide6](https://img.shields.io/badge/UI-PySide6-green.svg)
![libtorrent](https://img.shields.io/badge/Engine-libtorrent-orange.svg)
![VLC](https://img.shields.io/badge/Player-VLC-red.svg)

O **CineTorrent** é um cliente de torrents desktop para Windows, construído inteiramente em Python. O projeto foi idealizado para ser leve, rápido e focado na experiência de assistir a vídeos enquanto o download ainda está em andamento (streaming progressivo).

*Este projeto foi idealizado, arquitetado e desenvolvido de forma autoral como parte do meu portfólio de desenvolvimento em Python.*

## ✨ Funcionalidades Principais

- **Download P2P Completo:** Suporte nativo a arquivos `.torrent` e links magnéticos (`magnet:`).
- **Otimização de Rede (Anti-Bloqueio):** Injeção automática de uma lista agressiva de 25 trackers públicos (fallback) para contornar torrents com trackers mortos. O sistema também utiliza criptografia de protocolo (`out_enc_policy` e `in_enc_policy`) para evitar o bloqueio de velocidade (throttling) por parte das operadoras.
- **Priorização de Streaming (BEP 9):** Ao selecionar um arquivo de vídeo dentro de um torrent, o código altera as prioridades das peças do libtorrent para baixar os primeiros megabytes o mais rápido possível, permitindo que o player abra antes do download terminar.
- **Barra de Progresso Customizada:** Diferente de barras convencionais, o app utiliza `QPainter` para desenhar blocos individuais representando cada "peça" (piece) do arquivo em tempo real, no estilo clássico de clientes como o BitTorrent.
- **Reprodução Integrada:** Utiliza a biblioteca `python-vlc` para instanciar o player de mídia (VLC 64-bit) nativamente. O código monitora o tamanho do arquivo no disco e só invoca o VLC quando há dados suficientes (mais de 2 MB) para evitar travamentos de reprodução.
- **Diagnóstico de Rede em Tempo Real:** Painel que exibe status detalhado da DHT, Trackers, Peers, Seeders e velocidades de upload/download.
- **Gerenciamento Seguro:** O evento de fechamento (`closeEvent`) faz o *release* explícito do VLC, limpa a sessão do libtorrent e encerra o processo do Python (via `os._exit`) de forma limpa, evitando processos órfãos no Windows.

## 🛠️ Tecnologias e Bibliotecas

- **[Python 3.13](https://www.python.org/)**: Linguagem base.
- **[PySide6](https://doc.qt.io/qtforpython/)**: Framework oficial da Qt para a criação da interface gráfica.
- **[libtorrent 2.x](https://www.libtorrent.org/)**: Engine P2P em C++ (com bindings Python) que gerencia o protocolo BitTorrent, DHT, trackers e conexões TCP/uTP.
- **[python-vlc](https://wiki.videolan.org/Python_bindings/)**: Integração do VLC Media Player com o Python.

## 🚀 Como Executar

### Pré-requisitos
1. **Python 3.13** instalado (recomendado para manter a compatibilidade com a build do libtorrent).
2. **VLC Media Player 64-bit** instalado no sistema ([Download oficial](https://www.videolan.org/vlc/)).

### Passo a Passo

1. Clone o repositório:
```bash
git clone https://github.com/dada1000/CineTorrent.git
cd CineTorrent
