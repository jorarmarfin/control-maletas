<?php
/**
 * Emite una clave de licencia CM2 para "Control Maletas".
 * Requiere PHP >= 7.2 con la extensión sodium (viene incluida).
 *
 * La clave privada es la SEMILLA de 32 bytes en base64 (contenido de keys/private.key).
 * Guárdela solo en el servidor (variable de entorno / fuera del webroot), NUNCA en el navegador.
 *
 * Uso CLI:  CM_LICENSE_PRIVATE_KEY=... php generar_clave.php "Retiro Octubre" "Parroquia" 2026-10-01 2026-10-31 500
 */

function b64url(string $raw): string
{
    return rtrim(strtr(base64_encode($raw), '+/', '-_'), '=');
}

/**
 * @param string      $seedB64   semilla Ed25519 (32 bytes) en base64
 * @param string      $type      'event' | 'master'
 * @param string|null $event     nombre EXACTO del evento (obligatorio si type=event)
 */
function generar_clave_cm2(
    string $seedB64,
    string $type,
    ?string $event,
    string $licensee,
    ?string $startsAt,
    ?string $endsAt,
    ?int $maxPeople
): string {
    $seed = base64_decode($seedB64, true);
    if ($seed === false || strlen($seed) !== SODIUM_CRYPTO_SIGN_SEEDBYTES) {
        throw new InvalidArgumentException('Semilla Ed25519 inválida');
    }
    $keypair = sodium_crypto_sign_seed_keypair($seed);
    $secret  = sodium_crypto_sign_secretkey($keypair);

    $payload = [
        'id'         => bin2hex(random_bytes(6)),
        'type'       => $type,
        'event'      => $type === 'event' ? $event : null,
        'licensee'   => $licensee,
        'starts_at'  => $startsAt,   // 'YYYY-MM-DD' o null
        'ends_at'    => $endsAt,     // 'YYYY-MM-DD' o null
        'max_people' => $maxPeople,  // int o null (sin límite)
        'issued_at'  => date('Y-m-d'),
    ];
    // Se firman los bytes EXACTOS que viajan en la clave: no hay que canonicalizar nada.
    $json = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    $sig  = sodium_crypto_sign_detached($json, $secret);

    return 'CM2.' . b64url($json) . '.' . b64url($sig);
}

if (PHP_SAPI === 'cli' && realpath($_SERVER['SCRIPT_FILENAME']) === __FILE__) {
    [$_, $event, $licensee, $from, $to, $max] = array_pad($argv, 6, null);
    $seed = getenv('CM_LICENSE_PRIVATE_KEY') ?: trim(@file_get_contents(__DIR__ . '/../../keys/private.key'));
    echo generar_clave_cm2($seed, 'event', $event, $licensee ?? '', $from, $to, $max !== null ? (int)$max : null), PHP_EOL;
}
