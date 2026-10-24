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

## Qué hay

| Build | Cómo | Fuente |
|---|---|---|
| PHP 8.x (`php`, `php-fpm`, `xdebug.so`) | [static-php-cli](https://github.com/crazywhalecc/static-php-cli) con el target glibc 2.17 (corre en cualquier distro con glibc ≥ 2.17 y puede cargar `xdebug.so`) | [php.net](https://www.php.net/downloads.php), [xdebug.org](https://xdebug.org/download) |
| nginx | estático, en Alpine (pcre2, zlib, OpenSSL) | [nginx.org](https://nginx.org/en/download.html) |
| Redis | estático, en Alpine | [download.redis.io](https://download.redis.io/releases/) |

## Licencias

Los workflows y scripts de este repo son MIT ([LICENSE](LICENSE)). Cada binario lleva la licencia de
su proyecto: PHP License (PHP), Xdebug License, BSD-2 (nginx) y, en Redis 8, RSALv2 / SSPLv1 / AGPLv3
a elegir: las fuentes exactas de cada build son las del enlace de su release y este repo.
