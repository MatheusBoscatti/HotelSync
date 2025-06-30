from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .models import Reserva, Quarto, Hospede, Receita, Despesa, Relatorio
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from django.utils.timezone import now
from django.db.models import Sum
from django.db.models.functions import TruncMonth

Usuario = get_user_model()

def index(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'easyhosts/index.html')

def relato(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'easyhosts/relato.html')

def politicas(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'easyhosts/politicas.html')

def cd2(request):
    return render(request, 'easyhosts/cd2.html')

def suporte(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'easyhosts/supor.html')

def configuracao(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'easyhosts/config.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            request.session['user_name'] = user.username
            return redirect('index')
        else:
            messages.error(request, 'Usuário ou senha incorretos.')
    
    return render(request, 'easyhosts/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def checkin_view(request):
    """
    Visualização da página de check-in com listagem de reservas ativas
    """
    # Buscar todas as reservas confirmadas
    reservas = Reserva.objects.filter(status='confirmada').order_by('-data_checkin')
    hoje = datetime.now().date()
    
    # Buscar todos os quartos (para edição)
    todos_quartos = Quarto.objects.all()
    
    # Buscar quartos disponíveis (para novo check-in)
    quartos_ocupados = Reserva.objects.filter(
        status='confirmada',
        data_checkin__lte=hoje,
        data_checkout__gte=hoje
    ).values_list('quarto_id', flat=True)
    
    quartos_disponiveis = todos_quartos.exclude(id__in=quartos_ocupados)
    
    context = {
        'reservas': reservas,
        'quartos': todos_quartos,  # Passamos todos os quartos para o template
        'quartos_disponiveis': quartos_disponiveis,  # Para uso futuro se necessário
        'today': hoje
    }
    
    return render(request, 'easyhosts/checkin.html', context)

@login_required
def get_reserva(request, reserva_id):
    """Endpoint para obter dados de uma reserva específica"""
    try:
        reserva = Reserva.objects.get(id=reserva_id)
        return JsonResponse({
            'id': reserva.id,
            'nome_completo': reserva.hospede.nome_completo,
            'telefone': reserva.hospede.telefone,
            'cpf': reserva.hospede.cpf if hasattr(reserva.hospede, 'cpf') else '',
            'email': reserva.hospede.email if hasattr(reserva.hospede, 'email') else '',
            'data_checkin': reserva.data_checkin.strftime('%Y-%m-%d'),
            'data_checkout': reserva.data_checkout.strftime('%Y-%m-%d') if reserva.data_checkout else '',
            'quarto': reserva.quarto.numero_quarto,
            'observacoes': reserva.observacoes or ''
        })
    except Reserva.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Reserva não encontrada'}, status=404)

@login_required
@csrf_exempt
def criar_checkin(request):
    """
    Endpoint para criar um novo check-in
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validar dados obrigatórios
            if not all([data.get('nome_completo'), data.get('telefone'), data.get('data_checkin'), data.get('quarto')]):
                return JsonResponse({'status': 'error', 'message': 'Campos obrigatórios faltando'}, status=400)
            
            # Processar datas
            data_checkin = datetime.strptime(data['data_checkin'], '%Y-%m-%d').date()
            data_checkout = datetime.strptime(data['data_checkout'], '%Y-%m-%d').date() if data.get('data_checkout') else None
            
            # Verificar quarto
            quarto = Quarto.objects.get(numero_quarto=data['quarto'])
            
            # Criar ou atualizar hóspede
            hospede, created = Hospede.objects.get_or_create(
                cpf=data['cpf'],
                defaults={
                    'cpf': data.get('cpf'),
                    'email': data.get('email'),
                    'telefone': data.get('telefone'),
                    'nome_completo': data.get('nome_completo')
                }
            )
            
            if not created:
                if data.get('cpf') and hasattr(hospede, 'cpf'):
                    hospede.cpf = data['cpf']
                if data.get('email') and hasattr(hospede, 'email'):
                    hospede.email = data['email']
                hospede.save()
            
            # Criar reserva
            reserva = Reserva.objects.create(
                quarto=quarto,
                hospede=hospede,
                data_checkin=data_checkin,
                data_checkout=data_checkout,
                status='confirmada',
                observacoes=data.get('observacoes', '')
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Check-in criado com sucesso',
                'id': reserva.id
            })
            
        except Quarto.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Quarto não encontrado'}, status=400)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Formato de data inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

@login_required
@csrf_exempt
def update_reserva(request, reserva_id):
    """Endpoint para atualizar uma reserva existente"""
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            reserva = Reserva.objects.get(id=reserva_id)
            
            # Atualizar dados básicos
            reserva.data_checkin = datetime.strptime(data['data_checkin'], '%Y-%m-%d').date()
            reserva.data_checkout = datetime.strptime(data['data_checkout'], '%Y-%m-%d').date() if data.get('data_checkout') else None
            reserva.observacoes = data.get('observacoes', '')
            
            # Verificar se o quarto foi alterado
            if data['quarto'] != reserva.quarto.numero_quarto:
                reserva.quarto = Quarto.objects.get(numero_quarto=data['quarto'])
            
            # Atualizar dados do hóspede
            hospede = reserva.hospede
            hospede.nome_completo = data['nome_completo']
            hospede.telefone = data['telefone']
            if hasattr(hospede, 'cpf'):
                hospede.cpf = data.get('cpf', '')
            if hasattr(hospede, 'email'):
                hospede.email = data.get('email', '')
            hospede.save()
            
            reserva.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Reserva atualizada com sucesso'
            })
            
        except Reserva.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Reserva não encontrada'}, status=404)
        except Quarto.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Quarto não encontrado'}, status=400)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Formato de data inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

@login_required
def buscar_checkins(request):
    """Endpoint para buscar check-ins com filtros"""
    termo_busca = request.GET.get('termo', '')
    
    reservas = Reserva.objects.filter(status='confirmada')
    
    if termo_busca:
        reservas = reservas.filter(
            hospede__nome_completo__icontains=termo_busca
        ) | reservas.filter(
            quarto__numero_quarto__icontains=termo_busca
        )
    
    resultados = []
    for reserva in reservas:
        resultados.append({
            'id': reserva.id,
            'data_checkin': reserva.data_checkin.strftime('%d/%m/%Y'),
            'data_checkout': reserva.data_checkout.strftime('%d/%m/%Y') if reserva.data_checkout else None,
            'nome_completo': reserva.hospede.nome_completo,
            'telefone': reserva.hospede.telefone,
            'cpf': getattr(reserva.hospede, 'cpf', ''),
            'email': getattr(reserva.hospede, 'email', ''),
            'quarto': reserva.quarto.numero_quarto
        })
    
    return JsonResponse({'reservas': resultados})

    # views.py
@login_required
def hospedes_view(request):
    """
    Visualização da página de hóspedes
    """
    hospedes = Hospede.objects.all().order_by('-data_cadastro')
    
    context = {
        'hospedes': hospedes,
        'user_name': request.session.get('user_name', '')
    }
    
    return render(request, 'easyhosts/hospede.html', context)

@login_required
@csrf_exempt
def criar_hospede(request):
    """
    Endpoint para criar um novo hóspede
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else request.POST
            
            # Validar dados obrigatórios
            if not all([data.get('nome_completo'), data.get('telefone')]):
                return JsonResponse({'status': 'error', 'message': 'Nome e telefone são obrigatórios'}, status=400)
            
            # Criar hóspede
            hospede = Hospede.objects.create(
                nome_completo=data['nome_completo'],
                telefone=data['telefone'],
                cpf=data.get('cpf'),
                email=data.get('email'),
                observacoes=data.get('observacoes', '')
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Hóspede criado com sucesso',
                'id': hospede.id
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

@login_required
def buscar_hospedes(request):
    """
    Endpoint para buscar hóspedes com filtros
    """
    termo_busca = request.GET.get('termo', '')
    
    hospedes = Hospede.objects.all()
    
    if termo_busca:
        hospedes = hospedes.filter(
            nome_completo__icontains=termo_busca
        ) | hospedes.filter(
            cpf__icontains=termo_busca
        ) | hospedes.filter(
            email__icontains=termo_busca
        ) | hospedes.filter(
            telefone__icontains=termo_busca
        )
    
    resultados = []
    for hospede in hospedes:
        resultados.append({
            'id': hospede.id,
            'nome_completo': hospede.nome_completo,
            'telefone': hospede.telefone,
            'cpf': hospede.cpf or '-',
            'email': hospede.email or '-',
            'status': hospede.get_status_display(),
            'status_class': hospede.status
        })
    
    return JsonResponse({'hospedes': resultados})

    # views.py
@login_required
def get_hospede(request, hospede_id):
    """Endpoint para obter dados de um hóspede específico"""
    try:
        hospede = Hospede.objects.get(id=hospede_id)
        return JsonResponse({
            'id': hospede.id,
            'nome_completo': hospede.nome_completo,
            'telefone': hospede.telefone,
            'cpf': hospede.cpf or '',
            'email': hospede.email or '',
            'observacoes': hospede.observacoes or ''
        })
    except Hospede.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Hóspede não encontrado'}, status=404)

@login_required
@csrf_exempt
def update_hospede(request, hospede_id):
    """Endpoint para atualizar um hóspede existente"""
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            hospede = Hospede.objects.get(id=hospede_id)
            
            # Atualizar dados do hóspede
            hospede.nome_completo = data['nome_completo']
            hospede.telefone = data['telefone']
            hospede.cpf = data.get('cpf', '')
            hospede.email = data.get('email', '')
            hospede.observacoes = data.get('observacoes', '')
            
            hospede.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Hóspede atualizado com sucesso'
            })
            
        except Hospede.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Hóspede não encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)


        # views.py
@login_required
def quartos_view(request):
    hoje = now().date()

    # Buscar todos os quartos
    quartos = Quarto.objects.all()

    # Mapear reservas ativas (check-in feito e não finalizado)
    reservas_ativas = Reserva.objects.filter(
        status='confirmada',
        data_checkin__lte=hoje,
        data_checkout__gte=hoje
    )

    quartos_ocupados = {reserva.quarto.id: reserva for reserva in reservas_ativas}

    lista_quartos = []
    print(quartos_ocupados)
    for quarto in quartos:
        if quarto.id in quartos_ocupados:
            reserva = quartos_ocupados[quarto.id]
            status = 'ocupado'
            hospede = reserva.hospede.nome_completo
            data_checkin = reserva.data_checkin.strftime('%d/%m/%Y')
            data_checkout = reserva.data_checkout.strftime('%d/%m/%Y') if reserva.data_checkout else ''
        else:
            status = 'disponivel'
            hospede = ''
            data_checkin = ''
            data_checkout = ''

        lista_quartos.append({
            'numero': quarto.numero_quarto,
            'tipo': quarto.get_tipo_display(),
            'status': status,
            'hospede': hospede,
            'data_checkin': data_checkin,
            'data_checkout': data_checkout
        })

    context = {
        'quartos_info': lista_quartos
    }

    return render(request, 'easyhosts/quartos.html', context)

@login_required
def criar_quarto(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            numero_quarto = data.get('numero_quarto')
            tipo = data.get('tipo')

            if not numero_quarto or not tipo:
                return JsonResponse({'status': 'error', 'message': 'Todos os campos são obrigatórios'}, status=400)

            if Quarto.objects.filter(numero_quarto=numero_quarto).exists():
                return JsonResponse({'status': 'error', 'message': 'Número de quarto já existe'}, status=400)

            Quarto.objects.create(numero_quarto=numero_quarto, tipo=tipo)
            return JsonResponse({'status': 'success', 'message': 'Quarto criado com sucesso'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

        # views.py
@login_required
def transfer_view(request):
    """
    Visualização da página de hóspedes
    """
    transfer = Receita.objects.all()
    
    context = {
        'transfer': transfer,
        'user_name': request.session.get('user_name', '')
    }
    
    return render(request, 'easyhosts/transfer.html', context)

@login_required
def despes_view(request):
    """
    Visualização da página de hóspedes
    """
    despes = Despesa.objects.all()
    
    context = {
        'despes': despes,
        'user_name': request.session.get('user_name', '')
    }
    
    return render(request, 'easyhosts/despes.html', context)


@login_required
@csrf_exempt
def criar_receita(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nova_receita = Receita.objects.create(
                data=data['data'],
                descricao=data['descricao'],
                tipo=data['tipo'],
                forma_pagamento=data['forma_pagamento'],
                valor=data['valor']
            )
            return JsonResponse({'status': 'success', 'message': 'Receita criada com sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

@login_required
@csrf_exempt
def criar_despesa(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nova_despesa = Despesa.objects.create(
                data=data['data'],
                descricao=data['descricao'],
                tipo=data['tipo'],
                forma_pagamento=data['forma_pagamento'],
                responsavel=data['responsavel'],
                valor=data['valor']
            )
            return JsonResponse({'status': 'success', 'message': 'Despesa criada com sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)


@login_required
def exibir_graficos(request):
    # Definir o período (últimos 12 meses)
    today = datetime.now()
    twelve_months_ago = today.replace(year=today.year-1) if today.month == 12 else today.replace(month=today.month+1, year=today.year-1)
    
    # Agrupar receitas por mês
    receitas_mensais = Receita.objects.filter(
        data__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('data')
    ).values('month').annotate(
        total=Sum('valor')
    ).order_by('month')
    
    # Agrupar despesas por mês
    despesas_mensais = Despesa.objects.filter(
        data__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('data')
    ).values('month').annotate(
        total=Sum('valor')
    ).order_by('month')
    
    # Agrupar receitas por tipo
    receitas_por_tipo = Receita.objects.values('tipo').annotate(
        total=Sum('valor')
    ).order_by('-total')
    
    # Agrupar despesas por tipo
    despesas_por_tipo = Despesa.objects.values('tipo').annotate(
        total=Sum('valor')
    ).order_by('-total')
    
    # Converter QuerySets para listas de dicionários
    def queryset_to_list(qs):
        return [{'month': item['month'].strftime('%Y-%m-%d'), 'total': float(item['total'])} 
                if 'month' in item else 
                {'tipo': item['tipo'], 'total': float(item['total'])}
                for item in qs]
    
    context = {
        'receitas_mensais': json.dumps(queryset_to_list(receitas_mensais)),
        'despesas_mensais': json.dumps(queryset_to_list(despesas_mensais)),
        'receitas_por_tipo': json.dumps(queryset_to_list(receitas_por_tipo)),
        'despesas_por_tipo': json.dumps(queryset_to_list(despesas_por_tipo)),
        'user_name': request.session.get('user_name', '')
    }
    
    return render(request, 'easyhosts/graficos.html', context)


@login_required
def relato(request):
    relatorios = Relatorio.objects.all().order_by('-data_criacao')
    context = {
        'relatorios': relatorios,
        'user_name': request.session.get('user_name', '')
    }
    return render(request, 'easyhosts/relato.html', context)

@login_required
def criar_relatorio(request):
    if request.method == 'POST':
        try:
            # Verifica se é uma requisição AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                arquivo = request.FILES.get('arquivo')
                
                # Converte a data_criacao de string para date
                data_criacao_str = request.POST.get('data_criacao')
                data_criacao = datetime.strptime(data_criacao_str, '%Y-%m-%d').date()
                
                # Cria o relatório
                relatorio = Relatorio(
                    data_criacao=data_criacao,  # ADICIONAR este campo
                    nome=request.POST.get('nome'),
                    descricao=request.POST.get('descricao'),
                    tipo=request.POST.get('tipo'),
                    responsavel=request.POST.get('responsavel'),
                    observacoes=request.POST.get('observacoes', ''),
                    arquivo=arquivo
                )
                
                relatorio.save()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Relatório criado com sucesso',
                    'id': relatorio.id
                })
            else:
                # Fallback para requisições não-AJAX (caso jQuery não funcione)
                arquivo = request.FILES.get('arquivo')
                data_criacao_str = request.POST.get('data_criacao')
                data_criacao = datetime.strptime(data_criacao_str, '%Y-%m-%d').date()
                
                relatorio = Relatorio(
                    data_criacao=data_criacao,
                    nome=request.POST.get('nome'),
                    descricao=request.POST.get('descricao'),
                    tipo=request.POST.get('tipo'),
                    responsavel=request.POST.get('responsavel'),
                    observacoes=request.POST.get('observacoes', ''),
                    arquivo=arquivo
                )
                
                relatorio.save()
                
                # Redireciona de volta para a página de relatórios
                return redirect('relato')
                
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=500)
            else:
                # Para requisições não-AJAX, você pode mostrar uma mensagem de erro
                messages.error(request, f'Erro ao criar relatório: {str(e)}')
                return redirect('relato')
    
    # Se não for POST, redireciona para a página de relatórios
    return redirect('relato')
        

@login_required
def baixar_relatorio(request, relatorio_id):
    relatorio = get_object_or_404(Relatorio, id=relatorio_id)
    if relatorio.arquivo:
        file_path = relatorio.arquivo.path
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type="application/octet-stream")
                response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
                return response
    return HttpResponse('Arquivo não encontrado', status=404)

@login_required
@csrf_exempt
def excluir_relatorio(request, relatorio_id):
    if request.method == 'POST':
        try:
            relatorio = get_object_or_404(Relatorio, id=relatorio_id)
            relatorio.delete()
            return JsonResponse({
                'status': 'success',
                'message': 'Relatório excluído com sucesso'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido'
    }, status=405)

    