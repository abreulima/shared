# Cidade Sob Invasao - Web

Esta pasta contém a versão para navegador do jogo.

## Como abrir

O jogo funciona melhor através de um servidor local. A forma mais simples é:

```bash
cd web
python -m http.server 8000
```

Depois abre no browser:

```text
http://localhost:8000
```

## Controles

- `WASD` ou setas: mover
- `Mouse` ou `Espaço`: disparar
- `E`: especial
- `C`: oficina
- `Shift`: impulso
- `Z`: torreta
- `X`: mina
- `Enter`: começar no menu
- `R`: reiniciar no fim

## Nota

Se abrires `index.html` diretamente com `file://`, alguns navegadores podem bloquear o carregamento dos assets. Por isso o servidor local é a opção recomendada.
