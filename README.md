# MikroTik Config Generator

Ferramenta desktop em Python para gerar configuracoes MikroTik com interface grafica.

## O que este projeto faz

- conecta no roteador MikroTik pela API
- detecta versao e interfaces
- ajuda a montar configuracao de PPPoE, bridge, VLAN e firewall
- gera script `.rsc`
- pode ser empacotado para Linux, macOS e Windows

## Modos de uso

Voce pode usar de 2 formas:

- como usuario final: baixar o executavel pronto para seu sistema e apenas abrir
- como desenvolvedor/tecnico: rodar pelo codigo-fonte com Python

## Uso como usuario final

Se voce recebeu o programa ja compilado:

- no Windows: abra o arquivo `.exe`
- no Linux: abra o executavel gerado para Linux
- no macOS: abra o executavel gerado para macOS

O usuario final nao precisa instalar Python quando estiver usando a versao compilada.

Observacao importante:

- o executavel de Windows nao roda no Linux nem no macOS
- o executavel de Linux nao roda no Windows
- o executavel de macOS nao roda no Windows ou Linux

Cada sistema operacional precisa do seu proprio pacote.

## Executar pelo codigo-fonte

### Requisitos

- Python 3.12 ou superior
- `pip`
- Tkinter/Tk instalado no sistema

### Instalar dependencias

```bash
pip install -r requirements.txt
```

### Iniciar a aplicacao

```bash
python main.py
```

No Linux, voce tambem pode usar:

```bash
./run-gui.sh
```

## Linux

### Rodar pelo fonte

```bash
pip install -r requirements.txt
python main.py
```

ou:

```bash
./run-gui.sh
```

### Dependencia de Tk

Se aparecer erro de `tkinter`, instale o runtime Tk da sua distribuicao.

Exemplos:

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install python3-tk
```

Arch Linux:

```bash
sudo pacman -S tk
```

Fedora:

```bash
sudo dnf install python3-tkinter
```

### Gerar executavel para Linux

```bash
./build.sh
```

Arquivo gerado:

- `dist/MikroTik Config Generator`

## macOS

### Rodar pelo fonte

```bash
pip3 install -r requirements.txt
python3 main.py
```

### Dependencia de Tk

Em muitos casos, o Python oficial ja vem com Tk. Se nao vier, instale uma versao de Python com suporte a Tk.

### Gerar executavel para macOS

```bash
./build-macos.sh
```

O arquivo final sera criado em `dist/`.

## Windows

### Rodar pelo fonte

No Prompt de Comando ou PowerShell:

```powershell
pip install -r requirements.txt
python main.py
```

### Dependencia de Tk

Instale o Python oficial com suporte a Tkinter.

### Gerar executavel para Windows

```bat
build.bat
```

O arquivo final sera criado em `dist\`.

## Gerar pacotes pelo GitHub Actions

Este projeto possui workflow para build automatizado em:

- Linux
- macOS
- Windows

Arquivo do workflow:

- `.github/workflows/build.yml`

Depois de subir o projeto para o GitHub, voce pode:

1. abrir a aba `Actions`
2. executar o workflow manualmente, ou usar `push` para disparar o build
3. baixar os artefatos gerados para cada sistema

Assim, o usuario final so baixa o arquivo do sistema dele e executa.

## Estrutura principal

- `main.py`: ponto de entrada
- `gui/`: interface grafica
- `core/`: logica de conexao, deteccao e configuracao
- `templates/`: templates `.j2` para RouterOS v6 e v7
- `build.sh`: build para Linux
- `build-macos.sh`: build para macOS
- `build.bat`: build para Windows

## Observacoes

- revise o script gerado antes de aplicar em producao
- teste em laboratorio antes de usar em roteadores de clientes
- builds PyInstaller devem ser feitos no proprio sistema alvo ou via GitHub Actions
