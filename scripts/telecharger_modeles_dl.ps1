# Telecharge multilingual-e5-base (validation DL recherche) dans modeles/multilingual-e5-base,
# avec curl : reprise exacte apres chaque coupure reseau (le client Hugging Face repart de zero).
# Le notebook 05_dl_recherche.ipynb utilise ce dossier s'il existe, sinon le hub.
# Usage (depuis la racine) : .\scripts\telecharger_modeles_dl.ps1
$depot = "intfloat/multilingual-e5-base"
$dest = Join-Path $PSScriptRoot "..\modeles\multilingual-e5-base"
$fichiers = "config.json", "modules.json", "sentence_bert_config.json", "1_Pooling/config.json",
            "sentencepiece.bpe.model", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json",
            "model.safetensors"
foreach ($f in $fichiers) {
    $cible = Join-Path $dest $f
    New-Item -ItemType Directory -Force (Split-Path $cible) | Out-Null
    $url = "https://huggingface.co/$depot/resolve/main/$f"
    for ($essai = 1; $essai -le 200; $essai++) {
        Write-Host "=== $f (essai $essai) ===" -ForegroundColor Cyan
        curl.exe -L --fail -C - --retry 5 --retry-delay 5 --connect-timeout 30 --speed-limit 1000 --speed-time 60 -o $cible $url
        # 33 = le serveur refuse la reprise car le fichier est deja complet
        if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 33) { Write-Host "OK : $f" -ForegroundColor Green; break }
        Write-Host "Coupure (code $LASTEXITCODE), reprise dans 10 s..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
}
$taille = (Get-Item (Join-Path $dest "model.safetensors")).Length
Write-Host "model.safetensors : $taille octets (attendu 1112201288)"
if ($taille -eq 1112201288) { Write-Host "TERMINE" -ForegroundColor Green } else { Write-Host "INCOMPLET : relancer le script" -ForegroundColor Red }
