# -*- coding: utf-8 -*-
"""CineTorrent com lista agressiva de trackers, DHT otimizada, barra estilo BitTorrent e VLC.
Requer Windows, Python 3.13, VLC Desktop 64 bits.
Instalação: py -3.13 -m pip install PySide6 python-vlc libtorrent
"""
import os, sys
from pathlib import Path
import libtorrent as lt
import vlc
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QListWidget, QProgressBar, QMessageBox, QInputDialog, QGroupBox, QTextEdit)

OUT = Path.home() / "Videos" / "CineTorrent"
EXT = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".webm", ".m4v", ".mpg", ".mpeg", ".ts"}

FALLBACK_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.moeking.me:6969/announce",
    "udp://explodie.org:6969/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://tracker.tiny-vps.com:6969/announce",
    "udp://tracker.internetwarriors.net:1337/announce",
    "udp://tracker.leechers-paradise.org:6969/announce",
    "udp://tracker.coppersurfer.tk:6969/announce",
    "udp://tracker.zer0day.to:1337/announce",
    "udp://9.rarbg.to:2710/announce",
    "udp://9.rarbg.me:2710/announce",
    "udp://p4p.arenabg.com:1337/announce",
    "udp://tracker.cyberia.is:6969/announce",
    "udp://tracker.toss.li:6969/announce",
    "udp://opentracker.i2p.rocks:6969/announce",
    "udp://tracker.dler.org:6969/announce",
    "udp://tracker.army:6969/announce",
    "udp://tracker.birkenwald.de:6969/announce",
    "udp://tracker.bitsearch.to:1337/announce",
    "udp://tracker.0x7c0.com:6969/announce",
    "udp://tracker-udp.gbitt.info:80/announce",
    "udp://open.nyap2p.com:6969/announce"
]

def sizefmt(n):
    n = float(max(0, n or 0))
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB": return f"{n:.2f} {u}"
        n /= 1024

def val(obj, name, default=0):
    try: return getattr(obj, name)
    except Exception: return default

# --- COMPONENTE CUSTOMIZADO DA BARRA ESTILO BIT-TORRENT ---
class PieceBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(18)
        self.pieces = []
        self.have = []
        self.downloading = []

    def update_data(self, pieces, have, downloading):
        self.pieces = pieces
        self.have = have
        self.downloading = downloading
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        painter.fillRect(rect, QColor("#2b2b2b")) # Fundo cinza escuro (falta)
        
        total_pieces = len(self.pieces)
        if total_pieces == 0:
            painter.end()
            return

        # Calcula a largura de cada "bloquinho"
        piece_width = rect.width() / total_pieces
        gap = 0.5 # Espaçamento entre bloquinhos

        for i in range(total_pieces):
            x = i * piece_width
            w = max(1, piece_width - gap)
            
            # Define a cor
            if self.pieces[i] == 2: # Baixado (Azul)
                painter.fillRect(QRectF(x, 0, w, rect.height()), QColor("#3498db"))
            elif self.pieces[i] == 1: # Baixando (Verde)
                painter.fillRect(QRectF(x, 0, w, rect.height()), QColor("#2ecc71"))
            # Se for 0, fica a cor de fundo (cinza)
            
        painter.end()

# --- CLASSE DO TRABALHO ---
class Job:
    def __init__(self, handle, name, folder):
        self.handle, self.name, self.folder = handle, name, Path(folder)
        self.path, self.file_index = None, None
        self.waiting_play = False
        self.play_checks = 0

# --- INTERFACE PRINCIPAL ---
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CineTorrent — BitTorrent Style")
        self.resize(1040, 700)
        OUT.mkdir(parents=True, exist_ok=True)
        
        settings = {
            "listen_interfaces": "0.0.0.0:6881",
            "enable_dht": True,
            "enable_lsd": True,
            "enable_upnp": True,
            "enable_natpmp": True,
            "announce_to_all_trackers": True,
            "announce_to_all_tiers": True,
            "enable_outgoing_tcp": True,
            "enable_incoming_tcp": True,
            "enable_outgoing_utp": True,
            "enable_incoming_utp": True,
            "connections_limit": 2000,         
            "unchoke_slots_limit": 200,        
            "out_enc_policy": 1,               
            "in_enc_policy": 1,                
            "allowed_enc_level": 2,            
            "dht_bootstrap_nodes": "router.bittorrent.com:6881,router.utorrent.com:6881,dht.transmissionbt.com:6881,dht.libtorrent.org:25401"
        }
        
        self.session = lt.session(settings)

        self.jobs, self.current = [], None
        self.vlc_instance, self.player, self.vlc_error = None, None, ""
        try:
            self.vlc_instance = vlc.Instance("--no-video-title-show")
            self.player = self.vlc_instance.media_player_new()
        except Exception as e:
            self.vlc_error = str(e)
            
        self.ui()
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(1000)

    def ui(self):
        root = QWidget(); self.setCentralWidget(root); main = QVBoxLayout(root)
        box = QGroupBox("Adicionar torrent"); grid = QGridLayout(box)
        self.mag = QLineEdit(); self.mag.setPlaceholderText("magnet:?xt=urn:btih:...")
        grid.addWidget(QLabel("Magnet:"), 0, 0); grid.addWidget(self.mag, 0, 1)
        b = QPushButton("Adicionar magnet"); b.clicked.connect(self.add_magnet); grid.addWidget(b, 0, 2)
        b = QPushButton("Abrir .torrent"); b.clicked.connect(self.add_file); grid.addWidget(b, 1, 2)
        b = QPushButton("Forçar busca de fontes"); b.clicked.connect(self.reannounce); grid.addWidget(b, 2, 2)
        main.addWidget(box)
        
        row = QHBoxLayout(); self.items = QListWidget(); self.items.currentRowChanged.connect(self.select)
        self.items.setMinimumWidth(290); row.addWidget(self.items, 1)
        
        right = QVBoxLayout()
        self.name = QLabel("Adicione um torrent."); self.state = QLabel("Status: —")
        
        # --- SUBSTITUIÇÃO DA BARRINHA AQUI ---
        self.bar = PieceBar() 
        
        self.stats = QLabel("Sem download selecionado."); self.stats.setWordWrap(True)
        for w in (self.name, self.state, self.bar, self.stats): right.addWidget(w)
        
        controls = QGridLayout()
        for label, fn, pos in [
            ("Pausar/Retomar", self.pause, (0,0)), ("Selecionar / reproduzir", self.choose_video, (0,1)),
            ("Abrir pasta", self.open_folder, (1,0)), ("Remover torrent", self.remove, (1,1))]:
            b = QPushButton(label); b.clicked.connect(fn); controls.addWidget(b, *pos)
        right.addLayout(controls)
        
        diag = QGroupBox("Diagnóstico de rede e trackers"); dl = QVBoxLayout(diag)
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMinimumHeight(210); dl.addWidget(self.log)
        right.addWidget(diag)
        
        self.playmsg = QLabel("A reprodução antecipada depende da disponibilidade de peças e do índice do contêiner.")
        self.playmsg.setWordWrap(True); right.addWidget(self.playmsg); right.addStretch()
        
        row.addLayout(right, 2); main.addLayout(row)
        main.addWidget(QLabel(f"Pasta de download: {OUT}"))
        if self.vlc_error: self.playmsg.setText("VLC não inicializado: instale VLC Desktop 64 bits. " + self.vlc_error)

    def add_magnet(self):
        uri = self.mag.text().strip()
        if not uri.startswith("magnet:?"):
            QMessageBox.warning(self, "Magnet inválido", "O link deve começar com magnet:?"); return
        try:
            p = lt.parse_magnet_uri(uri)
            p.save_path = str(OUT)
            h = self.session.add_torrent(p)
            
            for tr in FALLBACK_TRACKERS:
                try: h.add_tracker(tr)
                except Exception: pass
                
            self.add_job(h, h.name() or "Magnet aguardando metadados", OUT); self.mag.clear()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao adicionar magnet: {e}")

    def add_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Abrir torrent", str(Path.home()), "Torrent (*.torrent)")
        if not f: return
        
        try:
            ti = lt.torrent_info(f)
        except Exception as e:
            QMessageBox.critical(self, "Erro no Arquivo", f"Arquivo .torrent corrompido.\n\nErro: {e}")
            return

        try:
            folder = OUT / ti.name()
            folder.mkdir(parents=True, exist_ok=True)
            info_hash_str = str(ti.info_hashes().v1)
            magnet_uri = f"magnet:?xt=urn:btih:{info_hash_str}&dn={ti.name()}"
                
            p = lt.parse_magnet_uri(magnet_uri)
            p.save_path = str(folder)
            h = self.session.add_torrent(p)
            
            for tr in FALLBACK_TRACKERS:
                try: h.add_tracker(tr)
                except Exception: pass
                    
            self.add_job(h, ti.name(), folder)
            QTimer.singleShot(1000, lambda handle=h: self.announce_now(handle))
            
        except Exception as e: 
            QMessageBox.critical(self, "Erro ao adicionar", str(e))

    def add_job(self, h, name, folder):
        j = Job(h, name, folder); self.jobs.append(j); self.items.addItem(name)
        self.items.setCurrentRow(len(self.jobs)-1)

    def select(self, n):
        self.current = self.jobs[n] if 0 <= n < len(self.jobs) else None
        self.refresh()

    def announce_now(self, h):
        try: h.force_reannounce()
        except Exception: pass
        try: h.force_dht_announce()
        except Exception: pass
        try: h.scrape_tracker()
        except Exception: pass

    def reannounce(self):
        if not self.current:
            QMessageBox.information(self, "CineTorrent", "Selecione um torrent.")
            return
        self.announce_now(self.current.handle)

    def write_log(self, message):
        self.log.append(message)

    def pause(self):
        if not self.current: return
        h = self.current.handle
        try:
            if h.status().paused:
                h.resume()
            else:
                h.pause()
        except Exception: pass

    def remove(self):
        if not self.current: 
            return
        answer = QMessageBox.question(self, "Remover torrent",
            f"Deseja remover '{self.current.name}' da lista?",
            QMessageBox.Yes | QMessageBox.No)
        if answer != QMessageBox.Yes: return
        
        try:
            index = self.jobs.index(self.current)
            self.session.remove_torrent(self.current.handle)
            self.jobs.pop(index); self.items.takeItem(index)
            self.current = None
            self.name.setText("Selecione um torrent."); self.state.setText("Status: —")
            self.stats.setText("Sem download selecionado."); self.log.clear()
            self.bar.update_data([], [], [])
        except Exception: pass

    def open_folder(self):
        if not self.current: return
        try: os.startfile(str(self.current.folder))
        except Exception: pass

    def choose_video(self):
        if not self.current:
            return
        try:
            h = self.current.handle
            ti = h.torrent_file()
            if ti is None:
                return
            files = ti.files()
            videos = []
            for i in range(files.num_files()):
                path = files.file_path(i)
                if Path(path).suffix.lower() in EXT:
                    videos.append((i, path))
                    
            if not videos: return
            options = [path for _, path in videos]
            selected, ok = QInputDialog.getItem(self, "Selecionar vídeo",
                "Escolha o vídeo que deseja reproduzir:", options, 0, False)
            if not ok: return
            index = next(i for i, path in videos if path == selected)
            self.current.file_index = index
            self.current.path = self.current.folder / selected
            priorities = [0] * files.num_files()
            priorities[index] = 7
            h.prioritize_files(priorities)
            self.current.waiting_play = True; self.current.play_checks = 0
            self.playmsg.setText("Vídeo selecionado. Aguardando dados...")
        except Exception: pass

    def try_playback(self, job):
        if not job.waiting_play or not job.path: return
        job.play_checks += 1
        if job.path.exists() and job.path.stat().st_size > 0:
            try:
                if job.path.stat().st_size > 2 * 1024 * 1024:
                    self.start_vlc(job.path)
                    job.waiting_play = False
                    return
            except Exception: pass
        if job.play_checks >= 300:
            job.waiting_play = False

    def start_vlc(self, path):
        if not self.player: return
        try:
            media = self.vlc_instance.media_new(str(path))
            self.player.set_media(media); self.player.play()
            self.playmsg.setText(f"Reproduzindo: {path.name}")
        except Exception: pass

    def refresh(self):
        if not self.current: return
        job = self.current; h = job.handle
        try:
            st = h.status()
            progress = float(val(st, "progress", 0) or 0)
            
            # --- ATUALIZA A BARRA CUSTOMIZADA AQUI ---
            # 0 = Não tem, 1 = Baixando, 2 = Completo
            self.bar.update_data(st.pieces, st.pieces, st.pieces) 
            
            downloaded = val(st, "total_wanted_done", 0)
            total = val(st, "total_wanted", 0)
            down = val(st, "download_rate", 0); up = val(st, "upload_rate", 0)
            peers = val(st, "num_peers", 0); seeds = val(st, "num_seeds", 0)
            dht_nodes = val(st, "num_dht_nodes", 0)
            
            self.name.setText(job.name)
            state = val(st, "state", "Desconhecido")
            self.state.setText(f"Status: {state} | Progresso: {progress * 100:.2f}%")
            self.stats.setText(
                f"Download: {sizefmt(down)}/s | Upload: {sizefmt(up)}/s\n"
                f"Baixado: {sizefmt(downloaded)} de {sizefmt(total)}\n"
                f"Peers: {peers} | Seeders: {seeds} | Nós DHT: {dht_nodes}"
            )
            self.try_playback(job)
        except Exception: pass

    def closeEvent(self, event):
        try: self.timer.stop()
        except Exception: pass
        try:
            if self.player:
                self.player.stop(); self.player.release()
            if self.vlc_instance:
                self.vlc_instance.release()
        except Exception: pass
        try:
            if hasattr(self, "session") and self.session:
                for job in self.jobs:
                    try: self.session.remove_torrent(job.handle)
                    except Exception: pass
                self.session.pause()
        except Exception: pass
        event.accept()
        os._exit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())