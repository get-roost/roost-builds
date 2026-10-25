# roost-builds

Los binarios de Linux que [Roost](https://github.com/get-roost/roost) instala y que no tienen un
binario oficial de upstream: **PHP** (con `php-fpm` y Xdebug), **nginx** y **Redis**. Se compilan
aquí, en GitHub Actions, a partir de las fuentes oficiales, y se publican como releases con su
`SHA256SUMS.txt` y attestations de procedencia de GitHub.

Lo que sí tiene binarios oficiales (MariaDB, MySQL, Node, Mailpit, cloudflared, Composer, Adminer)
Roost lo baja de upstream; Apache es el de la distribución.

## Cómo se verifica

Roost lleva fijado en su binario el SHA-256 de cada fichero que instala y lo comprueba antes de
extraer nada. Para comprobarlo a mano:

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
gh attestation verify php-8.4.27-nts-linux-x86_64.tar.gz --repo get-roost/roost-builds
```

Cada workflow comprueba antes las fuentes de upstream: el SHA-256 que publica php.net, la firma PGP
de nginx.org y el SHA-256 de `redis/redis-hashes`.

## Cómo se publica

**Solo, cada día:** `vigilar.yml` mira php.net (ramas 8.1 a 8.5) y la estable de nginx.org y, si hay una
versión que aún no está publicada aquí, lanza su workflow con `publish`: compila, prueba, publica la
release y, con `fijar-en-roost.yml`, abre un PR en `get-roost/roost` con los SHA-256 nuevos
(`scripts/fijar-en-roost.py`), que entran en la siguiente versión de Roost. Si algo no compila o no pasa
las pruebas, no se publica nada y al día siguiente se vuelve a intentar. El PR necesita el secreto
`ROOST_PR_TOKEN`: un token de grano fino con acceso solo a `get-roost/roost` y permisos *Contents* y *Pull
requests* de lectura y escritura. Sin él, el resumen del run dice qué fijar a mano.

**A mano:** lanzado con `workflow_dispatch`, un workflow solo compila, prueba y deja artefactos. Para
publicar, se lanza con `publish: true` y `from_run: <id del run probado>`: publica tal cual los
artefactos de ese run (los mismos bytes cuyo SHA-256 lleva Roost), sin recompilar. Una etiqueta
`php-<versión>` o `nginx-<versión>` compila y publica de cero; entonces hay que fijar en Roost los
SHA-256 de lo publicado.

## Qué hay

| Build | Cómo | Fuente |
|---|---|---|
| PHP 8.1–8.5 (`bin/php`, `bin/php-fpm`, `ext/xdebug.so`, `BUILD.json`, `licenses/`) | `php.yml`: [static-php-cli](https://github.com/crazywhalecc/static-php-cli) 3.0.0-alpha1 (rama `v3`, commit fijado) desde su fuente, `SPC_TARGET=x86_64-linux-gnu.2.17` (cualquier distro con glibc ≥ 2.17 y cualquier CPU x86_64), 40 extensiones integradas. Se comprueba `php -m`, `php-fpm -t` y sirviendo por FastCGI, Xdebug cargando, GLIBC ≤ 2.17, el arranque en centos:7, debian:10 y ubuntu:18.04 y en una CPU sin AVX (qemu) | [php.net](https://www.php.net/downloads.php), [xdebug.org](https://xdebug.org/download), verificadas con el SHA-256 que publican antes de compilar |
| nginx | `nginx.yml`: estático, en Alpine (pcre2, zlib, OpenSSL). Se comprueba `nginx -t` con una conf como la de Roost, sirviendo, recargando y parando | [nginx.org](https://nginx.org/en/download.html), verificada con su firma PGP y la huella del firmante fijada en el workflow |
| Redis | estático, en Alpine | [download.redis.io](https://download.redis.io/releases/) |

## Licencias

Los workflows y scripts de este repo son MIT ([LICENSE](LICENSE)). Cada binario lleva la licencia de
su proyecto: PHP License (PHP), Xdebug License, BSD-2 (nginx) y, en Redis 8, RSALv2 / SSPLv1 / AGPLv3
a elegir: las fuentes exactas de cada build son las del enlace de su release y este repo.
