#!/bin/bash

# Kritikos API - Script de desenvolvimento e testes
# Uso: ./run_api.sh [comando]

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de utilidade
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar se estamos no diretório correto
check_directory() {
    if [ ! -f "requirements_api.txt" ]; then
        log_error "Execute este script do diretório backend/"
        exit 1
    fi
}

# Instalar dependências
install_deps() {
    log_info "Instalando dependências da API..."
    pip install -r requirements_api.txt
    log_success "Dependências instaladas"
}

# Iniciar API localmente
start_api() {
    log_info "Iniciando API localmente..."
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    python -m api.main
}

# Iniciar API com reload (desenvolvimento)
start_dev() {
    log_info "Iniciando API em modo desenvolvimento (com reload)..."
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
}

# Subir serviços Docker
start_docker() {
    log_info "Subindo serviços com Docker..."
    cd ..
    docker-compose up -d db redis kritikos-api
    cd backend
    log_success "Serviços iniciados"
}

# Parar serviços Docker
stop_docker() {
    log_info "Parando serviços Docker..."
    cd ..
    docker-compose down
    cd backend
    log_success "Serviços parados"
}

# Ver logs Docker
logs_docker() {
    log_info "Exibindo logs da API..."
    cd ..
    docker-compose logs -f kritikos-api
    cd backend
}

# Testar API
test_api() {
    log_info "Executando testes da API..."
    python test_api_example.py
}

# Testar API em ambiente específico
test_api_remote() {
    local url=${1:-"http://localhost:8000"}
    log_info "Testando API em: $url"
    python test_api_example.py "$url"
}

# Verificar health check
health_check() {
    local url=${1:-"http://localhost:8000"}
    log_info "Verificando health check em: $url"
    curl -s "$url/health" | python -m json.tool || log_error "API não está respondendo"
}

# Formatar código
format_code() {
    log_info "Formatando código..."
    black api/ schemas/ services/ routers/ 2>/dev/null || log_warning "Black não instalado"
    isort api/ schemas/ services/ routers/ 2>/dev/null || log_warning "isort não instalado"
    log_success "Código formatado"
}

# Verificar tipos
check_types() {
    log_info "Verificando tipos com mypy..."
    mypy api/ 2>/dev/null || log_warning "mypy não instalado ou erros encontrados"
}

# Lint
lint_code() {
    log_info "Executando lint..."
    flake8 api/ 2>/dev/null || log_warning "flake8 não instalado ou erros encontrados"
}

# Limpar ambiente
clean() {
    log_info "Limpando ambiente..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    log_success "Ambiente limpo"
}

# Ajuda
show_help() {
    echo "Uso: $0 [comando]"
    echo ""
    echo "Comandos disponíveis:"
    echo "  install     Instalar dependências"
    echo "  start       Iniciar API localmente"
    echo "  dev         Iniciar API em modo desenvolvimento (com reload)"
    echo "  docker-up   Subir serviços com Docker"
    echo "  docker-down Parar serviços Docker"
    echo "  logs        Ver logs Docker"
    echo "  test        Testar API local"
    echo "  test-remote [url] Testar API remota"
    echo "  health [url] Verificar health check"
    echo "  format      Formatar código"
    echo "  types       Verificar tipos"
    echo "  lint        Executar lint"
    echo "  clean       Limpar ambiente"
    echo "  help        Mostrar esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0 install"
    echo "  $0 dev"
    echo "  $0 docker-up"
    echo "  $0 test"
    echo "  $0 test-remote http://api.kritikos.com.br"
}

# Main
main() {
    check_directory
    
    case "${1:-help}" in
        install)
            install_deps
            ;;
        start)
            start_api
            ;;
        dev)
            start_dev
            ;;
        docker-up)
            start_docker
            ;;
        docker-down)
            stop_docker
            ;;
        logs)
            logs_docker
            ;;
        test)
            test_api
            ;;
        test-remote)
            test_api_remote "$2"
            ;;
        health)
            health_check "$2"
            ;;
        format)
            format_code
            ;;
        types)
            check_types
            ;;
        lint)
            lint_code
            ;;
        clean)
            clean
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Comando desconhecido: $1"
            show_help
            exit 1
            ;;
    esac
}

# Executar main com todos os argumentos
main "$@"
