@echo off
REM Kritikos API - Script de desenvolvimento e testes para Windows
REM Uso: run_api.bat [comando]

setlocal enabledelayedexpansion

REM Verificar se estamos no diretório correto
if not exist "requirements_api.txt" (
    echo [ERRO] Execute este script do diretorio backend\
    exit /b 1
)

REM Processar argumentos
set COMMAND=%1
if "%COMMAND%"=="" set COMMAND=help

REM Instalar dependências
if "%COMMAND%"=="install" (
    echo [INFO] Instalando dependencias da API...
    pip install -r requirements_api.txt
    echo [SUCESSO] Dependencias instaladas
    goto :end
)

REM Iniciar API localmente
if "%COMMAND%"=="start" (
    echo [INFO] Iniciando API localmente...
    set PYTHONPATH=%PYTHONPATH%;%CD%
    python -m api.main
    goto :end
)

REM Iniciar API com reload (desenvolvimento)
if "%COMMAND%"=="dev" (
    echo [INFO] Iniciando API em modo desenvolvimento (com reload)...
    set PYTHONPATH=%PYTHONPATH%;%CD%
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
    goto :end
)

REM Subir serviços Docker
if "%COMMAND%"=="docker-up" (
    echo [INFO] Subindo servicos com Docker...
    cd ..
    docker-compose up -d db redis kritikos-api
    cd backend
    echo [SUCESSO] Servicos iniciados
    goto :end
)

REM Parar serviços Docker
if "%COMMAND%"=="docker-down" (
    echo [INFO] Parando servicos Docker...
    cd ..
    docker-compose down
    cd backend
    echo [SUCESSO] Servicos parados
    goto :end
)

REM Ver logs Docker
if "%COMMAND%"=="logs" (
    echo [INFO] Exibindo logs da API...
    cd ..
    docker-compose logs -f kritikos-api
    cd backend
    goto :end
)

REM Testar API
if "%COMMAND%"=="test" (
    echo [INFO] Executando testes da API...
    python test_api_example.py
    goto :end
)

REM Testar API em ambiente específico
if "%COMMAND%"=="test-remote" (
    set URL=%2
    if "%URL%"=="" set URL=http://localhost:8000
    echo [INFO] Testando API em: !URL!
    python test_api_example.py !URL!
    goto :end
)

REM Verificar health check
if "%COMMAND%"=="health" (
    set URL=%2
    if "%URL%"=="" set URL=http://localhost:8000
    echo [INFO] Verificando health check em: !URL!
    curl -s "!URL!/health" | python -m json.tool
    goto :end
)

REM Formatar código
if "%COMMAND%"=="format" (
    echo [INFO] Formatando codigo...
    black api/ schemas/ services/ routers/ 2>nul || echo [AVISO] Black nao instalado
    isort api/ schemas/ services/ routers/ 2>nul || echo [AVISO] isort nao instalado
    echo [SUCESSO] Codigo formatado
    goto :end
)

REM Verificar tipos
if "%COMMAND%"=="types" (
    echo [INFO] Verificando tipos com mypy...
    mypy api/ 2>nul || echo [AVISO] mypy nao instalado ou erros encontrados
    goto :end
)

REM Lint
if "%COMMAND%"=="lint" (
    echo [INFO] Executando lint...
    flake8 api/ 2>nul || echo [AVISO] flake8 nao instalado ou erros encontrados
    goto :end
)

REM Limpar ambiente
if "%COMMAND%"=="clean" (
    echo [INFO] Limpando ambiente...
    for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
    del /s /q *.pyc 2>nul
    del /s /q *.pyo 2>nul
    echo [SUCESSO] Ambiente limpo
    goto :end
)

REM Ajuda
if "%COMMAND%"=="help" (
    goto :show_help
)

if "%COMMAND%"=="--help" (
    goto :show_help
)

if "%COMMAND%"=="-h" (
    goto :show_help
)

REM Comando desconhecido
echo [ERRO] Comando desconhecido: %COMMAND%
goto :show_help

:show_help
echo Uso: %0 [comando]
echo.
echo Comandos disponiveis:
echo   install     Instalar dependencias
echo   start       Iniciar API localmente
echo   dev         Iniciar API em modo desenvolvimento (com reload)
echo   docker-up   Subir servicos com Docker
echo   docker-down Parar servicos Docker
echo   logs        Ver logs Docker
echo   test        Testar API local
echo   test-remote [url] Testar API remota
echo   health [url] Verificar health check
echo   format      Formatar codigo
echo   types       Verificar tipos
echo   lint        Executar lint
echo   clean       Limpar ambiente
echo   help        Mostrar esta ajuda
echo.
echo Exemplos:
echo   %0 install
echo   %0 dev
echo   %0 docker-up
echo   %0 test
echo   %0 test-remote http://api.kritikos.com.br

:end
endlocal
