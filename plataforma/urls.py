from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # TELA INICIAL E LOADING
    path('', views.loading_screen, name='loading'), # Inicia no 1% a 60% 
    
    # AUTENTICAÇÃO
    path('cadastro/', views.cadastro_view, name='cadastro'), # Cadastro com país e convite
    path('login/', views.login_view, name='login'), # Login com telefone
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # JOGO E INTERATIVIDADE
    path('jogo/', views.home_jogo, name='home_jogo'), # O Cassino de Dados
    path('apostar/', views.fazer_aposta, name='fazer_aposta'), # Lógica de investimento
    
    # --- ROTA CRÍTICA PARA CORREÇÃO DE SALDO ---
    path('processar-resultado/', views.processar_resultado_final, name='processar_resultado'),
    
    # FINANCEIRO E EQUIPA
    path('depositar/', views.depositar, name='depositar'), # 3 formas de depósito
    path('sacar/', views.sacar, name='sacar'), # Saque mínimo 2500kz
    path('convite/', views.pagina_convite, name='convite'), # Link e 15% de comissão 
    path('historico/', views.historico_view, name='historico'), # Depósitos, ganhos e perdas
]

