"""
CLI de envio sem visual (usada pelas tarefas do Windows e por automação). Todos os comandos aceitam --json.

  python postar.py login [--conta X]               # abre o Chrome da conta (normal, sem automacao) p/ logar
  python postar.py fila                            # videos e status por plataforma
  python postar.py plano                           # o que seria agendado e quando (nao envia nada)
  python postar.py agendar [-p tiktok,youtube,instagram]
  python postar.py enviar -p tiktok,youtube        # posta AGORA o proximo pendente de cada plataforma
  python postar.py enviar -p youtube --video limpos\\gta6_004.mp4
  python postar.py enviar -p tiktok --revisar      # preenche tudo mas nao publica
"""
import argparse
import json
import sys

from ..db import preparar
from ..plataformas import PLATAFORMAS, comum
from ..servicos import agenda, contas, postagem
from ..servicos.postagem import OK


def plats(s):
    ps = [p.strip() for p in s.split(",") if p.strip()]
    for p in ps:
        if p not in PLATAFORMAS:
            raise argparse.ArgumentTypeError(f"plataforma desconhecida: {p}")
    return ps


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Envio de videos")
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)
    todas = ",".join(PLATAFORMAS)
    for nome in ("login", "plano", "agendar", "enviar", "fila"):
        s = sub.add_parser(nome)
        s.add_argument("--conta", help="id da conta (padrao: a conta principal)")
        if nome != "fila":
            s.add_argument("-p", "--plataformas", type=plats, default=plats(todas))
        if nome == "enviar":
            s.add_argument("--video")
            s.add_argument("--revisar", action="store_true")
        if nome in ("plano", "agendar"):
            s.add_argument("--por-hora", type=int, help="modo lote: N posts por hora por plataforma")
            s.add_argument("--ate", help="modo lote: horario limite HH:MM (padrao 00:00 = meia-noite)")
    a = ap.parse_args()
    comum.JSON_MODE = a.json
    preparar()
    conta = contas.obter(a.conta)
    dump = lambda d: print(json.dumps(d, ensure_ascii=False, indent=1, default=str))

    if a.cmd == "login":
        postagem.abrir_login(conta, a.plataformas)
        print("Chrome da conta aberto. Faca login em cada aba e depois feche o Chrome inteiro.")
        return 0

    if a.cmd == "fila":
        itens = postagem.fila(conta)
        if a.json:
            return dump(itens) or 0
        print(f"{'video':<16}{'MB':>6}  " + "  ".join(f"{p:<14}" for p in PLATAFORMAS))
        for i in itens:
            print(f"{i['video']:<16}{i['mb']:>6}  " + "  ".join(f"{i[p]:<14}" for p in PLATAFORMAS))
        return 0

    if a.cmd in ("plano", "agendar"):
        p = agenda.plano(conta, a.plataformas, por_hora=a.por_hora, ate=a.ate)
        if a.cmd == "plano" or not p:
            if a.json:
                return dump([{**x, "video": x["video"].name} for x in p]) or 0
            for x in p:
                print(f"{x['quando']:%a %d/%m %H:%M}  {x['plataforma']:<10} {x['video'].name}")
            return 0
        res = postagem.executar(conta, p)
    else:
        tarefas = postagem.tarefas_envio(conta, a.plataformas, a.video)
        if not tarefas:
            comum.log(f"{a.video or 'fila'}: nada a fazer em {','.join(a.plataformas)}")
            return 0
        res = postagem.executar(conta, tarefas, revisar=a.revisar)

    if a.json:
        dump(res)
    return 0 if all(r["status"] in OK for r in res) else 1


if __name__ == "__main__":
    sys.exit(main())
