"""A classe Catalogo. Leia o README.md antes de começar.

Esta é a peça central do projeto: carrega o JSON uma vez, constrói os
índices no __init__ e expõe os 16 métodos que o main.py e o cli.py usam.
"""
import json
from collections import deque

class Catalogo:
    """Classe responsável pelo carregamento, limpeza de dados, indexação

    e consultas do catálogo TrilhaSonora.
    """

    def __init__(self, caminho_json: str):
        self._conteudos: dict[str, dict] = {}
        self._usuarios: dict[str, dict] = {}
        self._usuarios_por_nome_lower: dict[str, str] = {}
        self._generos_index: dict[str, set[str]] = {}
        self._fila: deque[str] = deque()

        self.abrir_e_indexar(caminho_json)

    def abrir_e_indexar(self, caminho_json: str) -> None:
        """Carrega o arquivo JSON e realiza a indexação em memória para buscas O(1)."""
        with open(caminho_json, "r", encoding="utf-8") as f:
            dados = json.load(f)

        # Indexa conteúdos e constrói o índice invertido de gêneros
        for c in dados.get("conteudos", []):
            cid = c["id"]
            self._conteudos[cid] = c

            generos = self._extrair_generos(c.get("generos"))
            for g in generos:
                if g not in self._generos_index:
                    self._generos_index[g] = set()
                self._generos_index[g].add(cid)

        # Indexa usuários por ID e por Nome
        for u in dados.get("usuarios", []):
            uid = u["id"]
            self._usuarios[uid] = u
            nome_lower = u["nome"].strip().lower()
            self._usuarios_por_nome_lower[nome_lower] = uid

    @staticmethod #independente do self
    def _extrair_generos(generos_raw) -> list[str]:
        """Trata gêneros (string, lista ou aninhados) e os retorna em ordem alfabética."""
        if not generos_raw:
            return []

        def _achatar(item):
            res = []
            if isinstance(item, str):
                res.append(item)
            elif isinstance(item, list):
                for sub in item:
                    res.extend(_achatar(sub))
            return res

        generos_flat = _achatar(generos_raw)
        return sorted(list(set(generos_flat)))

    @staticmethod #independente do self
    def _normalizar_data(data_str: str | None) -> str | None:
        """Converte datas no formato DD/MM/YYYY para o padrão ISO YYYY-MM-DD."""
        if not data_str:
            return None
        if "/" in data_str:
            partes = data_str.split("/")
            if len(partes) == 3:
                d, m, y = partes
                return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        return data_str

    # --- Usuários e Playlists ---

    def listar_usuarios(self) -> list[str]:
        nomes = [u["nome"] for u in self._usuarios.values()]
        return sorted(nomes)

    def buscar_usuario_por_nome(self, nome: str) -> str | None:
        if not nome:
            return None
        return self._usuarios_por_nome_lower.get(nome.strip().lower())

    def playlist_de(self, usuario_id: str) -> list[str] | None:
        if usuario_id not in self._usuarios:
            return None
        return list(self._usuarios[usuario_id].get("playlist", []))

    def conteudo_na_posicao(self, usuario_id: str, posicao: int) -> str | None:
        playlist = self.playlist_de(usuario_id)
        if playlist is None:
            return None
        if 0 <= posicao < len(playlist):
            return playlist[posicao]
        return None

    def intersecao_playlists(self, usuario_ids: list[str]) -> list[str]:
        if not usuario_ids:
            return []

        conjuntos = []
        for uid in usuario_ids:
            if uid not in self._usuarios:
                return []
            conjuntos.append(set(self._usuarios[uid].get("playlist", [])))

        intersecao = set.intersection(*conjuntos)
        return sorted(list(intersecao))

    # --- Dados de um Conteúdo ---

    def rating_de(self, conteudo_id: str) -> float | None:
        if conteudo_id not in self._conteudos:
            return None
        conteudo = self._conteudos[conteudo_id]
        rating = conteudo.get("rating")
        if rating is None:
            return None
        return float(rating)

    def duracao_total_de(self, conteudo_id: str) -> int | None:
        if conteudo_id not in self._conteudos:
            return None
        conteudo = self._conteudos[conteudo_id]
        tipo = conteudo.get("tipo")

        if tipo == "musica":
            return conteudo.get("duracao_seg")
        elif tipo == "album":
            faixas = conteudo.get("faixas", [])
            return sum(
                f["duracao_seg"]
                for f in faixas
                if f.get("duracao_seg") is not None
            )
        return None

    def generos_de(self, conteudo_id: str) -> list[str] | None:
        if conteudo_id not in self._conteudos:
            return None
        conteudo = self._conteudos[conteudo_id]
        return self._extrair_generos(conteudo.get("generos"))

    def plataformas_de(self, conteudo_id: str) -> list[str] | None:
        if conteudo_id not in self._conteudos:
            return None
        conteudo = self._conteudos[conteudo_id]
        plataformas = conteudo.get("plataformas")
        if plataformas is None:
            return []
        return sorted(list(plataformas))

    def data_adicionado_de(self, conteudo_id: str) -> str | None:
        if conteudo_id not in self._conteudos:
            return None
        conteudo = self._conteudos[conteudo_id]
        raw_data = conteudo.get("data_adicionado")
        return self._normalizar_data(raw_data)

    def execucoes_de(self, conteudo_id: str) -> int | None:
        if conteudo_id not in self._conteudos:
            return None
        conteudo = self._conteudos[conteudo_id]
        engajamento = conteudo.get("engajamento")
        if not engajamento:
            return None
        execs = engajamento.get("execucoes")
        if execs is None:
            return None
        if isinstance(execs, str):
            execs = int(execs.replace(",", ""))
        return int(execs)

    def conteudos_do_genero(self, genero: str) -> list[str]:
        cids = self._generos_index.get(genero, set())
        return sorted(list(cids))

    # --- Fila de Reprodução ---

    def enfileirar(self, conteudo_id: str) -> bool:
        if conteudo_id not in self._conteudos:
            return False
        self._fila.append(conteudo_id)
        return True

    def proximo(self) -> str | None:
        if self._fila:
            return self._fila.popleft()
        return None

    def fila_atual(self) -> list[str]:
        return list(self._fila)