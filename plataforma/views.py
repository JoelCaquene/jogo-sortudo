from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .models import (
    Usuario, Deposito, Saque, Rodada, Aposta, 
    ConfiguracaoSistema, MetodoBanco, MetodoExpress, MetodoReferencia
)
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from decimal import Decimal
from django.db.models import Sum
import random
import time
import json

# --- 1. TELA DE LOADING (1% A 60%) ---
def loading_screen(request):
    return render(request, 'plataforma/loading.html')

# --- 2. CADASTRO COM LÓGICA DE CONVITE E PAÍS ---
def cadastro_view(request):
    if request.method == 'POST':
        telefone = request.POST.get('telefone')
        password = request.POST.get('password')
        pais = request.POST.get('pais')
        invite_code = request.POST.get('invite_code')

        if Usuario.objects.filter(telefone=telefone).exists():
            messages.error(request, "Este número já está cadastrado.")
            return redirect('cadastro')

        # Criar usuário
        user = Usuario.objects.create_user(telefone=telefone, password=password)
        user.pais = pais
        
        # Lógica de Convite
        if invite_code:
            try:
                padrinho = Usuario.objects.get(telefone=invite_code)
                user.convidado_por = padrinho
            except Usuario.DoesNotExist:
                pass
        
        user.save()
        login(request, user)
        return redirect('loading')

    return render(request, 'plataforma/cadastro.html')

# --- 3. LOGIN POR TELEFONE ---
def login_view(request):
    if request.method == 'POST':
        telefone = request.POST.get('username')
        senha = request.POST.get('password')
        user = authenticate(request, telefone=telefone, password=senha)
        
        if user is not None:
            login(request, user)
            return redirect('loading')
        else:
            messages.error(request, "Telefone ou senha incorretos.")
    
    return render(request, 'plataforma/login.html')

# --- 4. TELA PRINCIPAL DO JOGO (SINCRONIZADA) ---
@login_required
def home_jogo(request):
    """
    Lógica de Sincronização Universal:
    Todos os usuários seguem o mesmo ciclo de 40 segundos baseado no tempo do servidor.
    0-30 segundos: Fase de Apostas.
    30-40 segundos: Fase de Sorteio/Resultado.
    """
    config = ConfiguracaoSistema.objects.first()
    
    # 1. Busca ou cria a rodada ativa
    rodada_ativa = Rodada.objects.filter(ativa=True).last()
    if not rodada_ativa:
        rodada_ativa = Rodada.objects.create(ativa=True)

    # 2. Cálculo do Tempo Universal (Sincroniza todos os navegadores)
    agora = int(time.time())
    tempo_no_ciclo = agora % 40  # Ciclo total de 40 segundos
    
    if tempo_no_ciclo < 30:
        # Fase de Apostas (0 a 29 segundos)
        fase_atual = "APOSTA"
        tempo_restante = 30 - tempo_no_ciclo
    else:
        # Fase de Sorteio (30 a 39 segundos)
        fase_atual = "SORTEIO"
        tempo_restante = 40 - tempo_no_ciclo

    # 3. Retorno para o Template
    return render(request, 'plataforma/jogo.html', {
        'usuario': request.user, 
        'config': config,
        'rodada': rodada_ativa,
        'tempo_inicial': tempo_restante,
        'fase_inicial': fase_atual,
        'saldo_exibido': float(request.user.saldo)
    })

# --- 5. LÓGICA DE APOSTA COM CONTROLO DE SALDO ---
@login_required
def fazer_aposta(request):
    if request.method == 'POST':
        try:
            # Converte e valida os dados recebidos
            valor_investido = Decimal(request.POST.get('valor_investido', 0))
            numero_escolhido = int(request.POST.get('numero_escolhido'))
            usuario = request.user

            # 1. Validação de Saldo
            if usuario.saldo < valor_investido:
                return JsonResponse({'erro': 'Saldo insuficiente!'}, status=400)

            # 2. Busca a Rodada Ativa
            rodada = Rodada.objects.filter(ativa=True).last()
            
            if not rodada:
                rodada = Rodada.objects.create(ativa=True)

            # 3. Criação da Aposta
            nova_aposta = Aposta.objects.create(
                usuario=usuario,
                rodada=rodada,
                valor_escolhido=numero_escolhido,
                valor_investido=valor_investido
            )
            
            # 4. Atualização do Saldo do Usuário (Retira o valor imediatamente)
            usuario.saldo -= valor_investido
            usuario.save()
            
            return JsonResponse({
                'sucesso': 'Aposta realizada com sucesso!',
                'aposta_id': nova_aposta.id,
                'novo_saldo': float(usuario.saldo)
            })

        except (ValueError, TypeError):
            return JsonResponse({'erro': 'Dados de aposta inválidos.'}, status=400)
        except Exception as e:
            return JsonResponse({'erro': f'Erro interno: {str(e)}'}, status=500)

    return JsonResponse({'erro': 'Método inválido'}, status=405)

# --- NOVA FUNÇÃO: PROCESSAR RESULTADO FINAL (CORREÇÃO DE SALDO) ---
@login_required
def processar_resultado_final(request):
    """
    Esta função é chamada via AJAX para confirmar se o usuário ganhou ou perdeu.
    Garante que o saldo não volte ao estado anterior ao recarregar a página.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            resultado_dado = int(data.get('resultado'))
            aposta_id = data.get('aposta_id')

            aposta = get_object_or_404(Aposta, id=aposta_id, usuario=request.user)
            
            # Evita processamento duplo
            if aposta.ganhou is not None:
                 return JsonResponse({'status': 'processado', 'novo_saldo': float(request.user.saldo)})

            # Lógica de Ganho
            if aposta.valor_escolhido == resultado_dado:
                aposta.ganhou = True
                lucro = aposta.valor_investido * Decimal(resultado_dado)
                request.user.saldo += lucro # Adiciona o prêmio
                request.user.save()
            else:
                aposta.ganhou = False
                # O saldo já foi retirado em fazer_aposta, então aqui apenas confirmamos a perda no DB
            
            aposta.save()

            return JsonResponse({
                'ganhou': aposta.ganhou,
                'novo_saldo': float(request.user.saldo)
            })
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)
    return JsonResponse({'erro': 'Inválido'}, status=400)

# --- 6. LÓGICA DE DEPÓSITO ---
@login_required
def depositar(request):
    config = ConfiguracaoSistema.objects.first()
    bancos = MetodoBanco.objects.filter(ativo=True)
    express = MetodoExpress.objects.filter(ativo=True)
    referencias = MetodoReferencia.objects.filter(ativo=True)
    valores_pre = config.valores_pre_definidos.split(',') if config else []

    if request.method == 'POST':
        metodo = request.POST.get('metodo')
        valor = request.POST.get('valor')
        nome = request.POST.get('nome_depositante')
        comprovativo = request.FILES.get('comprovativo')

        Deposito.objects.create(
            usuario=request.user,
            metodo=metodo,
            valor=valor,
            nome_depositante=nome,
            comprovativo=comprovativo
        )
        messages.success(request, "Depósito enviado! Aguarde a aprovação.")
        return redirect('home_jogo')

    return render(request, 'plataforma/depositar.html', {
        'config': config, 'bancos': bancos, 'express': express, 
        'referencias': referencias, 'valores_pre': valores_pre
    })

# --- 7. LÓGICA DE RESULTADO (CASA GANHA SEMPRE) ---
def fechar_rodada_lucrativa(rodada_id):
    rodada = Rodada.objects.get(id=rodada_id)
    opcoes = [0, 2, 3, 4, 5, 6]
    gastos_por_opcao = {}
    
    for opt in opcoes:
        total_apostado = Aposta.objects.filter(rodada=rodada, valor_escolhido=opt).aggregate(Sum('valor_investido'))['valor_investido__sum'] or 0
        if opt == 0:
            gastos_por_opcao[opt] = total_apostado
        else:
            gastos_por_opcao[opt] = total_apostado * opt

    numero_vencedor = min(gastos_por_opcao, key=gastos_por_opcao.get)
    rodada.numero_sorteado = numero_vencedor
    rodada.ativa = False
    rodada.save()

    apostas = Aposta.objects.filter(rodada=rodada)
    for aposta in apostas:
        if aposta.valor_escolhido == numero_vencedor:
            aposta.ganhou = True
            if numero_vencedor == 0:
                aposta.usuario.saldo += aposta.valor_investido
            else:
                aposta.usuario.saldo += (aposta.valor_investido * Decimal(numero_vencedor))
            aposta.usuario.save()
        else:
            aposta.ganhou = False
        aposta.save()

# --- 8. SAQUE ---
@login_required
def sacar(request):
    if request.method == 'POST':
        valor = Decimal(request.POST.get('valor'))
        if valor < 2500:
            messages.error(request, "O valor mínimo para saque é 2500 Kz.")
            return redirect('sacar')
        
        if request.user.saldo >= valor:
            Saque.objects.create(usuario=request.user, valor=valor)
            request.user.saldo -= valor
            request.user.save()
            messages.success(request, "Pedido de saque realizado!")
        else:
            messages.error(request, "Saldo insuficiente.")
            
    return render(request, 'plataforma/sacar.html', {'usuario': request.user})

# --- 9. EQUIPA E CONVITE ---
@login_required
def pagina_convite(request):
    subordinados = Usuario.objects.filter(convidado_por=request.user)
    return render(request, 'plataforma/convite.html', {
        'usuario': request.user,
        'subordinados': subordinados,
        'total_sub': subordinados.count()
    })

# --- 10. HISTÓRICO ---
@login_required
def historico_view(request):
    apostas = Aposta.objects.filter(usuario=request.user).order_by('-id')
    depositos = Deposito.objects.filter(usuario=request.user).order_by('-data_criacao')
    saques = Saque.objects.filter(usuario=request.user).order_by('-data_pedido')
    
    return render(request, 'plataforma/historico.html', {
        'apostas': apostas, 'depositos': depositos, 'saques': saques
    })
    