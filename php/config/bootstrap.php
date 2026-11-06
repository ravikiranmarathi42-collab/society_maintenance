<?php
if (session_status() !== PHP_SESSION_ACTIVE) {
    $secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');
    session_set_cookie_params(['httponly'=>true, 'secure'=>$secure, 'samesite'=>'Lax']);
    session_start();
}
require_once __DIR__ . '/database.php';
function e($value): string { return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function csrf_token(): string { if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(32)); return $_SESSION['csrf']; }
function verify_csrf(): void { if ($_SERVER['REQUEST_METHOD']==='POST' && !hash_equals($_SESSION['csrf'] ?? '', $_POST['csrf'] ?? '')) { http_response_code(403); exit('Invalid security token. Refresh and try again.'); } }
function user(): ?array { return $_SESSION['user'] ?? null; }
function require_login(): void { if (!user()) { header('Location: index.php?page=login'); exit; } }
function require_admin(): void { require_login(); if ((user()['role'] ?? '') !== 'admin') { http_response_code(403); exit('Administrator access required.'); } }
function flash(string $message, string $type='success'): void { $_SESSION['flash']=['message'=>$message,'type'=>$type]; }
function redirect(string $page='dashboard'): never { header('Location: index.php?page='.rawurlencode($page)); exit; }
