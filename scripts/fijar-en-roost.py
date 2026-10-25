#!/usr/bin/env python3
"""Fija en una copia de get-roost/roost los SHA-256 de lo publicado en las releases de roost-builds.

  fijar-en-roost.py php   <carpeta-de-roost> [--ramas 8.5,8.4] [--run <id>]
  fijar-en-roost.py nginx <carpeta-de-roost> [--run <id>]

php: por cada rama (todas las que haya publicadas si no se dice), la última release php-<rama>.<n>, el
tamaño de su tar.gz y su SHA-256 (del SHA256SUMS.txt de la release), en el `Pinned` de
src/Roost.Core/Install/LinuxPhpCatalog.cs. nginx: la última release nginx-<versión>, en NginxCatalog.Linux
de src/Roost.Core/Install/NginxInstaller.cs. Solo lee: las releases son públicas; con GH_TOKEN, la API no
corta a 60 peticiones por hora. Escribe en CAMBIOS (si está) lo que ha cambiado, para el cuerpo del PR, y
sale con 0 aunque no haya nada que cambiar. Sin dependencias: solo la biblioteca estándar.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "get-roost/roost-builds")
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def get(url, raw=False):
    headers = {"User-Agent": "roost-builds", "Accept": "application/vnd.github+json"}
    if os.environ.get("GH_TOKEN") and url.startswith("https://api.github.com/"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    data = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60).read()
    return data.decode("utf-8") if raw else json.loads(data)


def releases():
    out, page = [], 1
    while True:
        batch = get(f"https://api.github.com/repos/{REPO}/releases?per_page=100&page={page}")
        out += [r for r in batch if not r["draft"]]
        if len(batch) < 100:
            return out
        page += 1


def version_key(v):
    return tuple(int(p) for p in v.split("."))


def asset(release, name):
    return next((a for a in release["assets"] if a["name"] == name), None)


def published(release, file):
    """(sha256, tamaño) del fichero de la release, con el SHA-256 de su SHA256SUMS.txt."""
    tar, sums = asset(release, file), asset(release, "SHA256SUMS.txt")
    if tar is None or sums is None:
        sys.exit(f"La release {release['tag_name']} no trae {file} y SHA256SUMS.txt")
    for line in get(sums["browser_download_url"], raw=True).splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == file:
            if not re.fullmatch(r"[0-9a-f]{64}", parts[0]):
                sys.exit(f"SHA256SUMS.txt de {release['tag_name']}: {parts[0]} no es un SHA-256")
            return parts[0], tar["size"]
    sys.exit(f"SHA256SUMS.txt de {release['tag_name']} no tiene {file}")


def today():
    d = datetime.date.today()
    return f"{d.day}-{MESES[d.month - 1]}-{d.year}"


def php(root, ramas, run):
    path = os.path.join(root, "src", "Roost.Core", "Install", "LinuxPhpCatalog.cs")
    text = open(path, encoding="utf-8").read()
    tags = {}
    for r in releases():
        m = re.fullmatch(r"php-(\d+\.\d+)\.(\d+)", r["tag_name"])
        if m and (m.group(1) not in tags or version_key(r["tag_name"][4:]) > version_key(tags[m.group(1)]["tag_name"][4:])):
            tags[m.group(1)] = r
    wanted = ramas or sorted(tags, key=version_key, reverse=True)
    changes = []
    for rama in wanted:
        if rama not in tags:
            sys.exit(f"No hay ninguna release php-{rama}.x en {REPO}")
        version = tags[rama]["tag_name"][4:]
        sha, size = published(tags[rama], f"php-{version}-nts-linux-x86_64.tar.gz")
        line = f'("{version}", "{sha}", {size:_}),'
        pattern = re.compile(r'\("' + re.escape(rama) + r'\.\d+", "[0-9a-f]{64}", [\d_]+\),')
        old = pattern.search(text)
        if old is None:
            sys.exit(f"LinuxPhpCatalog.cs no tiene la rama {rama} en Pinned: una rama nueva se añade a mano")
        if old.group(0) != line:
            changes.append(f"PHP {old.group(0).split(chr(34))[1]} -> {version} (SHA-256 {sha}, {size} bytes)")
            text = text[:old.start()] + line + text[old.end():]
    if changes and run:
        text = re.sub(r"Los tar\.gz del run \d+ de php\.yml \([^;]*;",
                      f"Los tar.gz del run {run} de php.yml ({today()};", text, count=1)
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    return changes


def nginx(root, run):
    path = os.path.join(root, "src", "Roost.Core", "Install", "NginxInstaller.cs")
    text = open(path, encoding="utf-8").read()
    rel = max((r for r in releases() if re.fullmatch(r"nginx-\d+\.\d+\.\d+", r["tag_name"])),
              key=lambda r: version_key(r["tag_name"][6:]), default=None)
    if rel is None:
        sys.exit(f"No hay ninguna release nginx-x.y.z en {REPO}")
    version = rel["tag_name"][6:]
    sha, size = published(rel, f"nginx-{version}-linux-x86_64.tar.gz")
    # El bloque de NginxCatalog.Linux: su comentario y el new(...) hasta el «);».
    block = re.search(r"    // nginx-\d+\.\d+\.\d+-linux-x86_64\.tar\.gz \([\d.]+ bytes\).*?public static readonly NginxBuild Linux = new\(.*?\);",
                      text, re.S)
    if block is None:
        sys.exit("NginxInstaller.cs no tiene el bloque de NginxCatalog.Linux como se espera")
    old_version = re.search(r'NginxBuild Linux = new\(\s*"(\d+\.\d+\.\d+)"', block.group(0)).group(1)
    old_sha = re.findall(r'"([0-9a-f]{64})"', block.group(0))[-1]
    if (old_version, old_sha) == (version, sha):
        return []
    new = block.group(0).replace(old_version, version).replace(old_sha, sha)
    new = re.sub(r"\([\d.]+ bytes\)", f"({size:,} bytes)".replace(",", "."), new, count=1)
    if run:
        new = re.sub(r"run \d+ de nginx\.yml, [^,]+,", f"run {run} de nginx.yml, {today()},", new, count=1)
    open(path, "w", encoding="utf-8", newline="\n").write(text[:block.start()] + new + text[block.end():])
    return [f"nginx {old_version} -> {version} (SHA-256 {sha}, {size} bytes); el de Windows (NginxCatalog.Windows) va aparte"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("producto", choices=["php", "nginx"])
    p.add_argument("roost")
    p.add_argument("--ramas", default="")
    p.add_argument("--run", default="")
    a = p.parse_args()
    ramas = [r for r in a.ramas.replace(" ", "").split(",") if r]
    changes = php(a.roost, ramas, a.run) if a.producto == "php" else nginx(a.roost, a.run)
    print("\n".join(changes) if changes else "Nada que cambiar: Roost ya lleva lo publicado.")
    if os.environ.get("CAMBIOS"):
        open(os.environ["CAMBIOS"], "w", encoding="utf-8").write("\n".join(f"- {c}" for c in changes))


if __name__ == "__main__":
    main()
